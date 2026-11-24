import re
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from . import services
from .models import MockIdentity

OAUTH_PARAMS = ("response_type", "client_id", "redirect_uri", "state", "code_challenge", "code_challenge_method")


def _redirect(redirect_uri, **params):
    return HttpResponseRedirect(f"{redirect_uri}?{urlencode(params)}")


@require_http_methods(["GET", "POST"])
def authorize(request):
    params = request.GET if request.method == "GET" else request.POST
    oauth = {k: params.get(k, "") for k in OAUTH_PARAMS}
    context = {
        **oauth,
        "frontend_url": settings.FRONTEND_URL,
        "test_accounts": MockIdentity.objects.values_list("email", "ra", "role"),
    }

    # Parâmetros inválidos: mostra erro e NUNCA redireciona (evita open redirect).
    if (
        oauth["response_type"] != "code"
        or oauth["client_id"] != settings.SSO_CLIENT_ID
        or oauth["redirect_uri"] not in settings.SSO_REDIRECT_URIS
        or oauth["code_challenge_method"] != "S256"  # PKCE obrigatório, como no OAuth 2.1
        or not re.fullmatch(r"[A-Za-z0-9_-]{43}", oauth["code_challenge"])
    ):
        context["fatal"] = "Requisição de autorização inválida (response_type, client_id, redirect_uri ou PKCE)."
        return render(request, "mock_sso/authorize.html", context, status=400)

    if request.method == "GET":
        return render(request, "mock_sso/authorize.html", context)

    if "cancel" in request.POST:
        return _redirect(oauth["redirect_uri"], error="access_denied", state=oauth["state"])

    login = request.POST.get("login", "")
    identity = services.authenticate(login, request.POST.get("password", ""))
    if identity is None:
        context.update(error="E-mail/RA ou senha incorretos.", login=login)
        return render(request, "mock_sso/authorize.html", context, status=401)

    code = services.issue_code(identity, oauth["client_id"], oauth["redirect_uri"], oauth["code_challenge"])
    return _redirect(oauth["redirect_uri"], code=code, state=oauth["state"])
