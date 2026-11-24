"""Serviço do Mock IdP. O MockSSOAdapter chama estas funções em processo (sem HTTP)."""

import secrets
from base64 import urlsafe_b64encode
from datetime import timedelta
from hashlib import sha256

from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.utils import timezone

from .models import AuthorizationCode, MockIdentity

CODE_TTL = timedelta(seconds=60)


def authenticate(login, password):
    """Login por e-mail ou RA (T15.3), como no SSO institucional."""
    login = login.strip()
    identity = login and MockIdentity.objects.filter(Q(email__iexact=login) | Q(ra=login)).first()
    return identity if identity and check_password(password, identity.password) else None


def issue_code(identity, client_id, redirect_uri, code_challenge):
    # ponytail: códigos usados/expirados ficam na tabela; limpar com um job se crescer.
    return AuthorizationCode.objects.create(
        code=secrets.token_urlsafe(32),
        identity=identity,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        expires_at=timezone.now() + CODE_TTL,
    ).code


def exchange_code(code, client_id, redirect_uri, code_verifier):
    """Troca o code (uso único) pelas claims da identidade. Retorna None se inválido/expirado/reusado
    ou se o code_verifier não gerar o code_challenge do authorize (PKCE S256, calculado aqui como um IdP real faria)."""
    challenge = urlsafe_b64encode(sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
    # UPDATE condicional é atômico: duas trocas simultâneas do mesmo code -> só uma vence.
    burned = AuthorizationCode.objects.filter(
        code=code, used=False, expires_at__gt=timezone.now(), client_id=client_id, redirect_uri=redirect_uri,
        code_challenge=challenge,
    ).update(used=True)
    if not burned:
        return None
    i = AuthorizationCode.objects.select_related("identity").get(code=code).identity
    return {"email": i.email, "name": i.name, "ra": i.ra, "role": i.role, "course": i.course}
