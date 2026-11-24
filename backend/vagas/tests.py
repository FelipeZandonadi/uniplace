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

    def candidatar(self, vaga, **data):
        return self.client.post(f"/api/vagas/{vaga.id}/candidatar/", data, format="json")

    def test_aluno_only_sees_open_vagas_of_own_course(self):
        Vaga.objects.create(titulo="Fechada", descricao=".", tipo="bolsa", prazo=self.vaga.prazo, aberta=False, autor=self.colab)
        ontem = timezone.localdate() - timedelta(days=1)
        Vaga.objects.create(titulo="Vencida", descricao=".", tipo="bolsa", prazo=ontem, autor=self.colab)
        self.login(self.aluno_med)
        self.assertEqual([v["titulo"] for v in self.client.get("/api/vagas/").json()["results"]], ["Bolsa"])
        self.assertEqual(self.candidatar(self.vaga).status_code, 404)
        self.login(self.aluno)
        self.assertEqual({v["titulo"] for v in self.client.get("/api/vagas/").json()["results"]}, {"Estágio", "Bolsa"})
        self.assertEqual(len(self.client.get("/api/vagas/?tipo=estagio").json()["results"]), 1)

    def test_candidatura_and_duplicate(self):
        self.login(self.aluno)
        resp = self.candidatar(self.vaga, mensagem="Tenho interesse")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], "enviada")
        self.assertEqual(resp.json()["vaga"], {"id": self.vaga.id, "titulo": "Estágio", "tipo": "estagio"})
        resp = self.candidatar(self.vaga)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["code"], "already_applied")
        vagas = {v["titulo"]: v["ja_candidatou"] for v in self.client.get("/api/vagas/").json()["results"]}
        self.assertEqual(vagas, {"Estágio": True, "Bolsa": False})
        self.assertEqual(len(self.client.get("/api/candidaturas/minhas/").json()["results"]), 1)

    def test_closed_or_expired_vaga(self):
        self.login(self.aluno)
        Vaga.objects.filter(pk=self.vaga.pk).update(aberta=False)
        self.assertEqual(self.candidatar(self.vaga).json()["code"], "vaga_fechada")
        Vaga.objects.filter(pk=self.geral.pk).update(prazo=timezone.localdate() - timedelta(days=1))
        resp = self.candidatar(self.geral)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "vaga_fechada")

    def test_only_colaborador_creates_and_only_owner_edits(self):
        payload = {"titulo": "Nova", "descricao": ".", "tipo": "monitoria", "prazo": "2030-01-01"}
        self.login(self.aluno)
        self.assertEqual(self.client.post("/api/vagas/", payload, format="json").status_code, 403)
        self.assertEqual(self.candidatar(self.vaga).status_code, 201)
        self.login(self.colab)
        resp = self.client.post("/api/vagas/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["autor"]["id"], self.colab.id)
        self.login(self.colab2)
        self.assertEqual(self.client.patch(f"/api/vagas/{self.vaga.id}/", {"aberta": False}, format="json").status_code, 403)
        self.assertEqual(self.client.get(f"/api/vagas/{self.vaga.id}/candidaturas/").status_code, 403)
        self.login(self.colab)
        resp = self.client.patch(f"/api/vagas/{self.vaga.id}/", {"aberta": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["aberta"])

    def test_only_vaga_owner_updates_candidatura_status(self):
        self.login(self.aluno)
        cand_id = self.candidatar(self.vaga).json()["id"]
        url = f"/api/candidaturas/{cand_id}/"
        self.assertEqual(self.client.patch(url, {"status": "aprovada"}, format="json").status_code, 403)
        self.login(self.colab2)
        self.assertEqual(self.client.patch(url, {"status": "aprovada"}, format="json").status_code, 403)
        self.login(self.colab)
        self.assertEqual(self.client.patch(url, {"status": "invalido"}, format="json").status_code, 400)
        resp = self.client.patch(url, {"status": "em_analise"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "em_analise")
        lista = self.client.get(f"/api/vagas/{self.vaga.id}/candidaturas/").json()["results"]
        self.assertEqual(lista[0]["aluno"]["email"], "aluno@uem.br")
