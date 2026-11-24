from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import TestCase

from .models import MockIdentity

VALID = {
    "response_type": "code", "client_id": "uniplace", "redirect_uri": settings.SSO_REDIRECT_URIS[0], "state": "s",
    "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM", "code_challenge_method": "S256",
}


class MockAuthorizeTests(TestCase):
    def setUp(self):
        MockIdentity.objects.create(
            email="aluno.teste@uem.br", name="Ana", ra="140001", role="aluno", password=make_password("teste123")
        )

    def test_open_redirect_is_blocked(self):
        evil = {**VALID, "redirect_uri": "https://evil.example.com/cb"}
        resp = self.client.get("/mock-sso/authorize/", evil)
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("Location", resp)
        resp = self.client.post("/mock-sso/authorize/", {**evil, "login": "aluno.teste@uem.br", "password": "teste123"})
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("Location", resp)

    def test_invalid_client_id(self):
        self.assertEqual(self.client.get("/mock-sso/authorize/", {**VALID, "client_id": "outro"}).status_code, 400)

    def test_pkce_is_required(self):
        for bad in ({"code_challenge": ""}, {"code_challenge_method": "plain"}, {"code_challenge": "curto"}):
            self.assertEqual(self.client.get("/mock-sso/authorize/", {**VALID, **bad}).status_code, 400)

    def test_cancel_redirects_with_access_denied(self):
        resp = self.client.post("/mock-sso/authorize/", {**VALID, "cancel": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], f"{VALID['redirect_uri']}?error=access_denied&state=s")

    def test_login_by_email_or_ra(self):
        def entrar(login, password="teste123"):
            return self.client.post("/mock-sso/authorize/", {**VALID, "login": login, "password": password}).status_code

        self.assertEqual(entrar(" ALUNO.teste@uem.br "), 302)
        self.assertEqual(entrar("140001"), 302)
        self.assertEqual(entrar("140001", "errada"), 401)
        MockIdentity.objects.create(email="prof@uem.br", name="P", role="professor", password=make_password("teste123"))
        self.assertEqual(entrar(" "), 401)  # login vazio não pode casar com o RA vazio do professor
