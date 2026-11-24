"""T15.3 — Carga inicial de dados mockados. Idempotente: pode rodar quantas vezes quiser."""

from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from accounts.sso import SSOIdentity
from mock_sso.models import MockIdentity
from mural.models import Aviso
from vagas.models import Vaga

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

        # Autores dos dados de exemplo (normalmente surgem no 1º login via SSO).
        prof, colab, admin = (User.objects.sync_from_sso(i) for i in IDENTIDADES[1:4])

        avisos = [
            ("Comunicado Oficial: Recesso Acadêmico", "alerta", "alta", admin,
             "Não haverá aulas entre 22/12 e 05/01. Os serviços administrativos funcionarão em regime de plantão."),
            ("Aviso: Prazo para Entrega de TCC", "prazo", "normal", prof,
             "A versão final do TCC deve ser enviada pelo sistema acadêmico até 05/12, às 23h59."),
            ("Cineclube UniPlace: Sessão Especial", "evento", "normal", colab,
             "Sessão especial no anfiteatro do bloco C, sexta-feira às 19h. Entrada gratuita."),
            ("Dicas de Estudo para o Semestre", "aviso", "normal", prof,
             "Organize um cronograma semanal, revise o conteúdo após cada aula e use os horários de monitoria."),
        ]
        for titulo, categoria, prioridade, autor, conteudo in avisos:
            Aviso.objects.get_or_create(
                titulo=titulo,
                defaults={"conteudo": conteudo, "categoria": categoria, "prioridade": prioridade, "autor": autor},
            )

        hoje = timezone.localdate()
        vagas = [
            ("Estágio em Desenvolvimento Web", "estagio", ES, colab, 30,
             "Estágio de 20h semanais em projetos com Python/Django e React. Bolsa-auxílio e auxílio-transporte."),
            ("Monitoria de Algoritmos e Estruturas de Dados", "monitoria", ES, admin, 15,
             "Apoio aos alunos do 1º ano em listas de exercícios e plantões de dúvidas. 12h semanais."),
            ("Bolsa de Iniciação Científica (PIBIC)", "bolsa", "", colab, 45,
             "Projeto de pesquisa em computação aplicada. Aberta a alunos de qualquer curso."),
        ]
        for titulo, tipo, curso, autor, dias, descricao in vagas:
            Vaga.objects.get_or_create(
                titulo=titulo,
                defaults={"descricao": descricao, "tipo": tipo, "curso": curso, "autor": autor,
                          "prazo": hoje + timedelta(days=dias)},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed OK: {MockIdentity.objects.count()} contas no Mock SSO (senha {SENHA_TESTE}), "
            f"{Aviso.objects.count()} avisos, {Vaga.objects.count()} vagas."
        ))
