"""Base própria do Mock IdP (Plano B). Simula o diretório institucional — isolada do resto da UniPlace."""

from django.db import models


class MockIdentity(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    ra = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20)
    course = models.CharField(max_length=120, blank=True)
    password = models.CharField(max_length=128)  # hash (make_password)

    class Meta:
        ordering = ["email"]
        verbose_name = "identidade (mock SSO)"
        verbose_name_plural = "identidades (mock SSO)"

    def __str__(self):
        return self.email


class AuthorizationCode(models.Model):
    code = models.CharField(max_length=64, unique=True)
    identity = models.ForeignKey(MockIdentity, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=64)
    redirect_uri = models.CharField(max_length=500)
    code_challenge = models.CharField(max_length=43)  # PKCE S256
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
