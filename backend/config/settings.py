"""Configurações do backend UniPlace. Tudo vem de variáveis de ambiente.

Fail-closed: sem DEBUG no ambiente vale produção (exige SECRET_KEY e SSO_ADAPTER=oidc). O manage.py liga
DEBUG=True por padrão só para comandos locais (runserver, test, seed); wsgi/asgi nunca herdam isso.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name, default):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-insecure-uniplace" if DEBUG else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY é obrigatória com DEBUG=False.")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", FRONTEND_URL)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "drf_spectacular_sidecar",  # assets do Swagger UI servidos localmente (funciona offline)
    "accounts",
    "mock_sso",
    "mural",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "NAME": os.environ.get("POSTGRES_DB", "uniplace"),
        "USER": os.environ.get("POSTGRES_USER", "uniplace"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "uniplace"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "accounts.exceptions.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "config.pagination.Paginacao",
    # ponytail: contadores no cache local (por processo); com vários workers, apontar CACHES para Redis.
    "DEFAULT_THROTTLE_RATES": {
        "publicacao": "30/hour",  # criação de avisos (com upload) e vagas, por usuário
        # Callback do SSO, por IP. No Wi-Fi do campus muitos alunos dividem um IP (NAT): suba LOGIN_RATE se preciso.
        "login": os.environ.get("LOGIN_RATE", "30/min"),
    },
    # De onde vem o IP do cliente nos limites por IP. 0 = REMOTE_ADDR (ignora X-Forwarded-For, que o cliente forja);
    # atrás de proxy reverso = quantos proxies confiáveis anexam o X-Forwarded-For.
    "NUM_PROXIES": int(os.environ.get("NUM_PROXIES", "0" if DEBUG else "1")),
}

# --- Documentação OpenAPI / Swagger (/api/docs/) ---
SPECTACULAR_SETTINGS = {
    "TITLE": "UniPlace API",
    "VERSION": "1.0.0 (Sprint 1 / MVP)",
    "DESCRIPTION": """
Hub de comunicação universitária da UEM. Erros seguem o formato `{"detail": "...", "code": "..."}`.

**Login (US01):** a UniPlace não guarda senhas. O login acontece no SSO institucional, acessado por um
**Adapter** (`MockSSOAdapter` no desenvolvimento — Plano B — ou `OIDCSSOAdapter` com o SSO real).
O backend troca o *authorization code* pela identidade, exige e-mail `@uem.br` e emite um JWT próprio:
access (15 min) no corpo da resposta + refresh rotacionado no cookie `HttpOnly` `uniplace_refresh`.

**Como obter um token aqui no Swagger** (tudo no mesmo navegador: o `start` grava o cookie do PKCE que o `callback` exige):
1. `GET /api/auth/sso/start/` → copie `authorize_url` e `state`.
2. Abra `authorize_url` no navegador (prefixe com `http://localhost:8000` ou `http://localhost:5173`)
   e entre com uma conta de teste (ex.: `prof.teste@uem.br` / `teste123`).
3. Você será redirecionado para `/auth/callback?code=...&state=...`: copie o `code` da barra de endereço
   (vale 60 s e é de uso único), mesmo que a página mostre erro.
4. `POST /api/auth/sso/callback/` com `{"code": "...", "state": "..."}`.
5. Copie o `access` da resposta, clique em **Authorize** e cole o token.
""",
    "TAGS": [
        {"name": "Autenticação", "description": "US01 — SSO via Adapter + JWT"},
        {"name": "Mural", "description": "US02/US03 — Mural de Avisos"},
        {"name": "Vagas", "description": "US08 — Oportunidades (estágio, bolsa, monitoria)"},
        {"name": "Candidaturas", "description": "US09 — Candidaturas às vagas"},
    ],
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,  # anexo aparece como upload binário no request
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    # Persistir o Bearer grava o token no localStorage (sobrevive ao logout): só em desenvolvimento.
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": DEBUG},
    # Docs públicas só em desenvolvimento; em produção, apenas admin (sessão do /admin/ ou Bearer).
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny" if DEBUG else "rest_framework.permissions.IsAdminUser"],
    "SERVE_AUTHENTICATION": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

REFRESH_COOKIE_NAME = "uniplace_refresh"
REFRESH_COOKIE_PATH = "/api/auth/"

# --- SSO (Adapter) ---
SSO_ADAPTER = os.environ.get("SSO_ADAPTER", "mock")  # "mock" | "oidc"
SSO_CLIENT_ID = os.environ.get("SSO_CLIENT_ID", "uniplace")
SSO_REDIRECT_URIS = env_list("SSO_REDIRECT_URIS", f"{FRONTEND_URL}/auth/callback")
SSO_ALLOWED_DOMAIN = os.environ.get("SSO_ALLOWED_DOMAIN", "uem.br")
if SSO_ADAPTER == "mock" and not DEBUG:
    raise ImproperlyConfigured("O Mock SSO só pode rodar com DEBUG=True; use SSO_ADAPTER=oidc.")

# Usado apenas com SSO_ADAPTER=oidc (SSO real da universidade).
OIDC_AUTHORIZE_URL = os.environ.get("OIDC_AUTHORIZE_URL", "")
OIDC_TOKEN_URL = os.environ.get("OIDC_TOKEN_URL", "")
OIDC_USERINFO_URL = os.environ.get("OIDC_USERINFO_URL", "")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
OIDC_SCOPE = os.environ.get("OIDC_SCOPE", "openid email profile")
OIDC_TIMEOUT = int(os.environ.get("OIDC_TIMEOUT", "5"))

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
