import secrets

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.core import signing
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import (
    api_view, authentication_classes, parser_classes, permission_classes, throttle_classes,
)
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import ApiError
from .models import User
from .serializers import UserSerializer, erro
from .sso import get_sso_adapter, pkce_challenge

STATE_SALT = "uniplace.sso.state"
STATE_MAX_AGE = 10 * 60
PKCE_COOKIE = "uniplace_pkce"
PKCE_COOKIE_PATH = "/api/auth/sso/"


class LoginThrottle(AnonRateThrottle):
    scope = "login"  # por IP (ver NUM_PROXIES no settings)

# --- Schemas só para o Swagger (as respostas reais são montadas nas views) ---
SESSION = OpenApiResponse(
    inline_serializer("Sessao", {"access": serializers.CharField(), "user": UserSerializer()}),
    description="Sessão criada. Também define o cookie `uniplace_refresh` (HttpOnly, SameSite=Strict, Path=/api/auth/).",
)
REFRESH_COOKIE = OpenApiParameter(
    "uniplace_refresh", str, OpenApiParameter.COOKIE, required=False,
    description="Refresh token. O navegador envia sozinho (HttpOnly); não é possível preencher via JavaScript.",
)


def _session_response(user, status_code=status.HTTP_200_OK):
    """Emite o JWT próprio da UniPlace: access no corpo, refresh em cookie HttpOnly."""
    refresh = RefreshToken.for_user(user)
    response = Response({"access": str(refresh.access_token), "user": UserSerializer(user).data}, status=status_code)
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="Strict",
        secure=not settings.DEBUG,
    )
    return response


def _check_origin(request):
    """refresh/logout se autenticam só pelo cookie. SameSite=Strict não barra form POST de outro site (a resposta
    ainda apagaria o cookie = logout forçado) nem subdomínios irmãos (*.uem.br). Navegadores sempre mandam Origin
    em POST cross-origin; clientes sem Origin (curl, testes) não carregam o cookie da vítima."""
    origin = request.headers.get("Origin")
    if origin and origin not in (*settings.CSRF_TRUSTED_ORIGINS, f"{request.scheme}://{request.get_host()}"):
        raise ApiError(403, "Origem da requisição não permitida.", "invalid_origin")


def _clear_cookie(response):
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH, samesite="Strict")
    return response


@extend_schema(
    tags=["Autenticação"], summary="1. Iniciar login no SSO",
    description="Também define o cookie `uniplace_pkce` (HttpOnly, 10 min) com o `code_verifier` do PKCE.",
    responses=inline_serializer("SSOStart", {"authorize_url": serializers.CharField(), "state": serializers.CharField()}),
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def sso_start(request):
    state = signing.dumps({"nonce": secrets.token_urlsafe(16)}, salt=STATE_SALT)
    verifier = secrets.token_urlsafe(48)  # 64 caracteres (RFC 7636: 43 a 128)
    response = Response({"authorize_url": get_sso_adapter().authorize_url(state, pkce_challenge(verifier)), "state": state})
    # O verifier nunca passa pela URL: fica só no navegador que iniciou o login, então um code vazado
    # (log de proxy, histórico, Referer) não pode ser trocado por sessão em outro lugar.
    response.set_cookie(
        PKCE_COOKIE, verifier, max_age=STATE_MAX_AGE, path=PKCE_COOKIE_PATH,
        httponly=True, samesite="Strict", secure=not settings.DEBUG,
    )
    return response


@extend_schema(
    tags=["Autenticação"], summary="2. Trocar o code do SSO por um JWT",
    request=inline_serializer("SSOCallback", {"code": serializers.CharField(), "state": serializers.CharField()}),
    responses={
        200: SESSION,
        400: erro(
            "`invalid_state` (state adulterado/expirado ou sem o cookie do PKCE) ou "
            "`invalid_code` (code inválido, expirado, reusado ou de outro navegador)"
        ),
        403: erro("`domain_not_allowed` (e-mail fora de @uem.br) ou `user_inactive`"),
        415: erro("Corpo precisa ser JSON"),
        429: erro("`throttled`: tentativas demais deste IP"),
        502: erro("`sso_unavailable` (IdP fora do ar)"),
    },
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
@parser_classes([JSONParser])  # form POST cross-site (login CSRF) recebe 415
def sso_callback(request):
    code, state = request.data.get("code"), request.data.get("state")
    verifier = request.COOKIES.get(PKCE_COOKIE)
    try:
        if not isinstance(state, str) or not verifier:  # sem o cookie, o login não começou neste navegador
            raise signing.BadSignature
        signing.loads(state, salt=STATE_SALT, max_age=STATE_MAX_AGE)
    except signing.BadSignature:  # inclui SignatureExpired
        raise ApiError(400, "Sessão de login inválida ou expirada. Tente novamente.", "invalid_state")
    if not isinstance(code, str) or not code:
        raise ApiError(400, "Código de autorização ausente.", "invalid_code")

    identity = get_sso_adapter().exchange_code(code, verifier)
    if not identity.email.lower().endswith("@" + settings.SSO_ALLOWED_DOMAIN):
        raise ApiError(
            403, f"Acesso restrito a contas institucionais @{settings.SSO_ALLOWED_DOMAIN}.", "domain_not_allowed"
        )
    user = User.objects.sync_from_sso(identity)
    if not user.is_active:
        raise ApiError(403, "Sua conta está desativada.", "user_inactive")
    update_last_login(None, user)
    response = _session_response(user)
    response.delete_cookie(PKCE_COOKIE, path=PKCE_COOKIE_PATH, samesite="Strict")
    return response


@extend_schema(
    tags=["Autenticação"], summary="Renovar a sessão (rotaciona o refresh do cookie)",
    request=None, parameters=[REFRESH_COOKIE],
    responses={
        200: SESSION,
        401: erro("`not_authenticated`: cookie ausente, expirado, revogado ou já usado"),
        403: erro("`invalid_origin`: requisição vinda de outra origem"),
    },
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def refresh(request):
    _check_origin(request)
    raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    try:
        if not raw:  # RefreshToken(None) criaria um token novo
            raise TokenError("missing")
        token = RefreshToken(raw)  # valida assinatura, expiração e blacklist
        user = User.objects.get(pk=token["user_id"], is_active=True)
        outstanding = OutstandingToken.objects.get(jti=token["jti"])
        # Rotação de uso único: se duas requisições usarem o mesmo refresh, só a primeira vence.
        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        if not created:
            raise TokenError("reused")
    except (TokenError, KeyError, User.DoesNotExist, OutstandingToken.DoesNotExist):
        return _clear_cookie(Response(
            {"detail": "Sessão expirada. Faça login novamente.", "code": "not_authenticated"},
            status=status.HTTP_401_UNAUTHORIZED,
        ))
    return _session_response(user)


@extend_schema(
    tags=["Autenticação"], summary="Sair (revoga o refresh e limpa o cookie)",
    request=None, parameters=[REFRESH_COOKIE],
    responses={204: None, 403: erro("`invalid_origin`: requisição vinda de outra origem")},
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def logout(request):
    _check_origin(request)
    raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if raw:
        try:
            RefreshToken(raw).blacklist()
        except TokenError:
            pass  # cookie inválido/expirado: logout é idempotente
    return _clear_cookie(Response(status=status.HTTP_204_NO_CONTENT))


@extend_schema(
    tags=["Autenticação"], summary="Usuário logado",
    responses={200: UserSerializer, 401: erro("`not_authenticated` ou `token_not_valid`")},
)
@api_view(["GET"])
def me(request):
    return Response(UserSerializer(request.user).data)
