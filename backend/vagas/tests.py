from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from mural.tests import make_user

from .models import Vaga

ES = "Engenharia de Software"


class VagaTests(APITestCase):
    def setUp(self):
        self.aluno = make_user("aluno@uem.br", "aluno", ES)
        self.aluno_med = make_user("med@uem.br", "aluno", "Medicina")
        self.colab = make_user("colab@uem.br", "colaborador")
        self.colab2 = make_user("colab2@uem.br", "colaborador")
        prazo = timezone.localdate() + timedelta(days=10)
        self.vaga = Vaga.objects.create(titulo="Estágio", descricao=".", tipo="estagio", curso=ES, prazo=prazo, autor=self.colab)
        self.geral = Vaga.objects.create(titulo="Bolsa", descricao=".", tipo="bolsa", prazo=prazo, autor=self.colab)

    def login(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")


    def test_aluno_only_sees_open_vagas_of_own_course(self):
        Vaga.objects.create(titulo="Fechada", descricao=".", tipo="bolsa", prazo=self.vaga.prazo, aberta=False, autor=self.colab)
        ontem = timezone.localdate() - timedelta(days=1)
        Vaga.objects.create(titulo="Vencida", descricao=".", tipo="bolsa", prazo=ontem, autor=self.colab)
        self.login(self.aluno_med)
        self.assertEqual([v["titulo"] for v in self.client.get("/api/vagas/").json()["results"]], ["Bolsa"])
        self.login(self.aluno)
        self.assertEqual({v["titulo"] for v in self.client.get("/api/vagas/").json()["results"]}, {"Estágio", "Bolsa"})
        self.assertEqual(len(self.client.get("/api/vagas/?tipo=estagio").json()["results"]), 1)



    def test_only_colaborador_creates_and_only_owner_edits(self):
        payload = {"titulo": "Nova", "descricao": ".", "tipo": "monitoria", "prazo": "2030-01-01"}
        self.login(self.aluno)
        self.assertEqual(self.client.post("/api/vagas/", payload, format="json").status_code, 403)
        self.login(self.colab)
        resp = self.client.post("/api/vagas/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["autor"]["id"], self.colab.id)
        self.login(self.colab2)
        self.assertEqual(self.client.patch(f"/api/vagas/{self.vaga.id}/", {"aberta": False}, format="json").status_code, 403)
        self.login(self.colab)
        resp = self.client.patch(f"/api/vagas/{self.vaga.id}/", {"aberta": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["aberta"])

