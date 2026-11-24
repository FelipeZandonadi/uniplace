"""T15.3 — Carga inicial de dados mockados. Idempotente: pode rodar quantas vezes quiser."""

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from accounts.sso import SSOIdentity
from mock_sso.models import MockIdentity

SENHA_TESTE = "teste123"
ES = "Engenharia de Software"

IDENTIDADES = [
    # O RA também serve de login no Mock IdP (RA/matrícula, como no SSO institucional).
    SSOIdentity("aluno.teste@uem.br", "Ana Aluna", "140001", "aluno", ES),
    SSOIdentity("prof.teste@uem.br", "Paulo Professor", "140002", "professor", ES),
    SSOIdentity("colab.teste@uem.br", "Carla Colaboradora", "140003", "colaborador", ""),
    SSOIdentity("admin.teste@uem.br", "Alberto Admin", "140004", "admin", ""),
    SSOIdentity("visitante@gmail.com", "Vitor Visitante", "140005", "aluno", ""),  # fora do domínio -> 403
]


class Command(BaseCommand):
    help = "Popula o Mock IdP e a UniPlace com contas, avisos e vagas de teste."

    @transaction.atomic
    def handle(self, *args, **options):
        for ident in IDENTIDADES:
            fields = {"name": ident.name, "ra": ident.ra, "role": ident.role, "course": ident.course}
            MockIdentity.objects.update_or_create(
                email=ident.email,
                defaults=fields,
                create_defaults={**fields, "password": make_password(SENHA_TESTE)},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed OK: {MockIdentity.objects.count()} contas no Mock SSO (senha {SENHA_TESTE}), "
        ))
