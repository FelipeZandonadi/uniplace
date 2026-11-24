"""Padrão Adapter para o SSO institucional (Etapa 2 — "Transição Transparente").

As views só conhecem a interface `SSOAdapter`. Trocar o Mock (Plano B) pelo SSO real da
universidade é mudar `SSO_ADAPTER=oidc` + variáveis OIDC_*, sem tocar na regra de negócio.
"""

import json
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from hashlib import sha256
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from .exceptions import ApiError
from .models import User


@dataclass(frozen=True)
class SSOIdentity:
    email: str
    name: str
    ra: str = ""
    role: str = User.Role.ALUNO
    course: str = ""


def pkce_challenge(verifier: str) -> str:
    """PKCE S256 (RFC 7636): o IdP só troca o code por quem apresentar o verifier que gerou este hash."""
    return urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def invalid_code():
    return ApiError(400, "Código de autorização inválido ou expirado. Faça login novamente.", "invalid_code")


class SSOUnavailable(ApiError):
    def __init__(self):
        super().__init__(502, "O SSO institucional está indisponível no momento. Tente novamente.", "sso_unavailable")


class SSOAdapter:
    def authorize_url(self, state: str, code_challenge: str) -> str:
        raise NotImplementedError

    def exchange_code(self, code: str, code_verifier: str) -> SSOIdentity:
        raise NotImplementedError

    @property
    def redirect_uri(self):
        return settings.SSO_REDIRECT_URIS[0]


class MockSSOAdapter(SSOAdapter):
    """Fala com o Mock IdP (app `mock_sso`) em processo, sem HTTP."""

    def authorize_url(self, state, code_challenge):
        query = urlencode({
            "response_type": "code",
            "client_id": settings.SSO_CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
        # URL relativa: o navegador passa pelo proxy do Vite (mesma origem do front).
        return f"/mock-sso/authorize/?{query}"

    def exchange_code(self, code, code_verifier):
        from mock_sso.services import exchange_code

        claims = exchange_code(code, settings.SSO_CLIENT_ID, self.redirect_uri, code_verifier)
        if claims is None:
            raise invalid_code()
        return SSOIdentity(**claims)


class OIDCSSOAdapter(SSOAdapter):
    # PKCE é retrocompatível (RFC 7636 §5): um IdP que não o suporte ignora os parâmetros extras.
    def authorize_url(self, state, code_challenge):
        query = urlencode({
            "response_type": "code",
            "client_id": settings.OIDC_CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "scope": settings.OIDC_SCOPE,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
        return f"{settings.OIDC_AUTHORIZE_URL}?{query}"

    def exchange_code(self, code, code_verifier):
        body = urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET,
            "code_verifier": code_verifier,
        }).encode()
        try:
            tokens = self._fetch_json(Request(settings.OIDC_TOKEN_URL, data=body))
        except HTTPError as e:
            if e.code in (400, 401):  # invalid_grant: code expirado/reutilizado
                raise invalid_code()
            raise SSOUnavailable()
        try:
            claims = self._fetch_json(Request(
                settings.OIDC_USERINFO_URL, headers={"Authorization": f"Bearer {tokens.get('access_token', '')}"}
            ))
        except HTTPError:
            raise SSOUnavailable()
        if not claims.get("email") or claims.get("email_verified") is not True:
            raise invalid_code()
        role = claims.get("role", User.Role.ALUNO)
        return SSOIdentity(
            email=claims["email"],
            name=claims.get("name", ""),
            ra=str(claims.get("ra", "")),
            role=role if role in User.Role.values else User.Role.ALUNO,
            course=claims.get("course", ""),
        )

    def _fetch_json(self, request):
        request.add_header("Accept", "application/json")
        try:
            with urlopen(request, timeout=settings.OIDC_TIMEOUT) as resp:
                return json.load(resp)
        except HTTPError:
            raise
        except (OSError, ValueError):  # URLError, timeout, conexão recusada, JSON inválido
            raise SSOUnavailable()


ADAPTERS = {"mock": MockSSOAdapter, "oidc": OIDCSSOAdapter}


def get_sso_adapter() -> SSOAdapter:
    return ADAPTERS[settings.SSO_ADAPTER]()
