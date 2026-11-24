import os
import subprocess
import sys
from io import StringIO
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from accounts.sso import OIDCSSOAdapter, pkce_challenge
from accounts.views import PKCE_COOKIE

COOKIE = settings.REFRESH_COOKIE_NAME


class SSOFlowTests(APITestCase):
    """Fluxo completo US01 pelas views HTTP reais: front -> Mock IdP -> callback -> JWT."""

    def setUp(self):
        cache.clear()  # contadores de rate limit não vazam entre testes
        call_command("seed", stdout=StringIO())

    def authorize(self, email, password="teste123"):
        """Simula o navegador: pega o authorize_url, faz login no Mock IdP e devolve (code, state)."""
        start = self.client.get("/api/auth/sso/start/")
        self.assertEqual(start.status_code, 200)
        url = urlsplit(start.json()["authorize_url"])
        self.assertEqual(url.path, "/mock-sso/authorize/")
        params = {k: v[0] for k, v in parse_qs(url.query).items()}

        page = self.client.get(url.path, params)
        self.assertContains(page, "Fazer login")

        resp = self.client.post(url.path, {**params, "login": email, "password": password})
        self.assertEqual(resp.status_code, 302)
        location = urlsplit(resp["Location"])
        self.assertEqual(f"{location.scheme}://{location.netloc}{location.path}", settings.SSO_REDIRECT_URIS[0])
        query = parse_qs(location.query)
        self.assertEqual(query["state"][0], start.json()["state"])
        return query["code"][0], query["state"][0]

    def callback(self, code, state):
        return self.client.post("/api/auth/sso/callback/", {"code": code, "state": state}, format="json")

    def test_happy_path_login_me_refresh_logout(self):
        resp = self.callback(*self.authorize("aluno.teste@uem.br"))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["user"], {
            "id": body["user"]["id"], "email": "aluno.teste@uem.br", "name": "Ana Aluna",
            "ra": "140001", "role": "aluno", "course": "Engenharia de Software",
        })
        cookie = resp.cookies[COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["path"], "/api/auth/")
        user = User.objects.get(email="aluno.teste@uem.br")
        self.assertFalse(user.has_usable_password())
        self.assertIsNotNone(user.last_login)

        me = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {body['access']}")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "aluno.teste@uem.br")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

        first_refresh = cookie.value
        resp = self.client.post("/api/auth/refresh/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.json())
        self.assertNotEqual(resp.cookies[COOKIE].value, first_refresh)

        current = resp.cookies[COOKIE].value
        self.client.cookies[COOKIE] = first_refresh
        self.assertEqual(self.client.post("/api/auth/refresh/").status_code, 401)

        self.client.cookies[COOKIE] = current
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.client.cookies[COOKIE] = current
        resp = self.client.post("/api/auth/refresh/")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["code"], "not_authenticated")

    def test_refresh_and_logout_without_cookie(self):
        self.assertEqual(self.client.post("/api/auth/refresh/").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)

    def test_login_syncs_role_from_idp(self):
        resp = self.callback(*self.authorize("prof.teste@uem.br"))
        self.assertEqual(resp.json()["user"]["role"], "professor")

    def test_domain_not_allowed(self):
        resp = self.callback(*self.authorize("visitante@gmail.com"))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], "domain_not_allowed")
        self.assertFalse(User.objects.filter(email="visitante@gmail.com").exists())

    def test_callback_rejects_form_post_login_csrf(self):
        code, state = self.authorize("aluno.teste@uem.br")
        resp = self.client.post("/api/auth/sso/callback/", {"code": code, "state": state})
        self.assertEqual(resp.status_code, 415)
        self.assertNotIn(COOKIE, resp.cookies)

    def test_tampered_state(self):
        code, state = self.authorize("aluno.teste@uem.br")
        resp = self.callback(code, state[:-2] + "xx")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "invalid_state")

    def test_code_is_single_use(self):
        code, state = self.authorize("aluno.teste@uem.br")
        verifier = self.client.cookies[PKCE_COOKIE].value
        self.assertEqual(self.callback(code, state).status_code, 200)
        self.client.cookies[PKCE_COOKIE] = verifier  # replay completo, com o verifier certo: o IdP ainda recusa
        resp = self.callback(code, state)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "invalid_code")

    def test_wrong_password_does_not_redirect(self):
        start = self.client.get("/api/auth/sso/start/").json()
        url = urlsplit(start["authorize_url"])
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        resp = self.client.post(url.path, {**params, "login": "aluno.teste@uem.br", "password": "errada"})
        self.assertEqual(resp.status_code, 401)
        self.assertContains(resp, "E-mail/RA ou senha incorretos", status_code=401)

    def test_pkce_stolen_code_is_useless_in_another_browser(self):
        code, state = self.authorize("aluno.teste@uem.br")
        atacante = APIClient()
        state_atacante = atacante.get("/api/auth/sso/start/").json()["state"]  # tem o próprio cookie/verifier
        resp = atacante.post("/api/auth/sso/callback/", {"code": code, "state": state_atacante}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "invalid_code")
        resp = self.callback(code, state)  # a vítima, com o verifier certo, ainda entra
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.cookies[PKCE_COOKIE]["max-age"], 0)  # verifier descartado após o uso

    def test_callback_without_pkce_cookie(self):
        code, state = self.authorize("aluno.teste@uem.br")
        del self.client.cookies[PKCE_COOKIE]
        resp = self.callback(code, state)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "invalid_state")

    def test_login_is_rate_limited_per_ip(self):
        junk = {"code": "x", "state": "x"}
        for _ in range(30):
            self.assertEqual(self.client.post("/api/auth/sso/callback/", junk, format="json").status_code, 400)
        resp = self.client.post("/api/auth/sso/callback/", junk, format="json", HTTP_X_FORWARDED_FOR="203.0.113.9")
        self.assertEqual(resp.status_code, 429)  # X-Forwarded-For forjado não zera o contador
        self.assertEqual(resp.json()["code"], "throttled")
        outro_ip = self.client.post("/api/auth/sso/callback/", junk, format="json", REMOTE_ADDR="10.0.0.2")
        self.assertEqual(outro_ip.status_code, 400)

    @override_settings(
        SSO_ADAPTER="oidc", OIDC_AUTHORIZE_URL="https://sso.uem.br/authorize",
        OIDC_TOKEN_URL="https://sso.uem.br/token", OIDC_USERINFO_URL="https://sso.uem.br/userinfo",
    )
    def test_oidc_adapter_sends_pkce(self):
        url = urlsplit(self.client.get("/api/auth/sso/start/").json()["authorize_url"])
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        verifier = self.client.cookies[PKCE_COOKIE].value
        self.assertEqual((query["code_challenge"], query["code_challenge_method"]), (pkce_challenge(verifier), "S256"))

        claims = {"email": "aluno.teste@uem.br", "email_verified": True, "name": "Ana"}
        with mock.patch.object(OIDCSSOAdapter, "_fetch_json", side_effect=[{"access_token": "t"}, claims]) as fetch:
            OIDCSSOAdapter().exchange_code("code-do-idp", verifier)
        token_request = parse_qs(fetch.call_args_list[0].args[0].data.decode())
        self.assertEqual(token_request["code_verifier"], [verifier])

    def test_cookie_endpoints_reject_foreign_origin(self):
        resp = self.callback(*self.authorize("aluno.teste@uem.br"))
        cookie = resp.cookies[COOKIE].value
        for path in ("/api/auth/refresh/", "/api/auth/logout/"):
            resp = self.client.post(path, {"x": "1"}, HTTP_ORIGIN="https://evil.uem.br")  # form POST cross-origin
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(resp.json()["code"], "invalid_origin")
            self.assertNotIn(COOKIE, resp.cookies)  # não apaga a sessão da vítima
        resp = self.client.post("/api/auth/refresh/", HTTP_ORIGIN=settings.FRONTEND_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.cookies[COOKIE].value, cookie)

    @override_settings(SSO_ADAPTER="oidc", OIDC_TOKEN_URL="http://127.0.0.1:9/token", OIDC_TIMEOUT=1)
    def test_real_sso_unavailable_returns_502(self):
        state = self.client.get("/api/auth/sso/start/").json()["state"]
        resp = self.callback("qualquer", state)
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["code"], "sso_unavailable")


class ProductionSettingsTests(SimpleTestCase):
    def test_wsgi_without_env_fails_closed(self):
        """Deploy sem variáveis não pode subir em DEBUG com a SECRET_KEY pública nem com o Mock SSO."""
        env = {k: v for k, v in os.environ.items() if k not in ("DEBUG", "SECRET_KEY", "SSO_ADAPTER")}

        def boot(**extra):
            cmd = [sys.executable, "-c", "import config.wsgi"]
            return subprocess.run(cmd, cwd=settings.BASE_DIR, env={**env, **extra}, capture_output=True, text=True).stderr

        self.assertIn("SECRET_KEY é obrigatória", boot())
        self.assertIn("Mock SSO só pode rodar com DEBUG=True", boot(SECRET_KEY="x" * 50))


class DocsTests(APITestCase):
    """Swagger público em desenvolvimento (DEBUG=True no ambiente; ver SPECTACULAR_SETTINGS)."""

    def test_swagger_and_schema(self):
        resp = self.client.get("/api/docs/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "swagger-ui")
        resp = self.client.get("/api/schema/?format=json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("/api/auth/sso/callback/", resp.json()["paths"])
