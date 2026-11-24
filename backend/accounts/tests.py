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
