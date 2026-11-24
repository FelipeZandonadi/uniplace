import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User

from .models import Aviso


def make_user(email, role, course=""):
    return User.objects.create_user(email, name=email.split("@")[0], role=role, course=course)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="uniplace-test-media-"))
class AvisoTests(APITestCase):
    def setUp(self):
        self.aluno = make_user("aluno@uem.br", "aluno")
        self.prof = make_user("prof@uem.br", "professor")
        self.prof2 = make_user("prof2@uem.br", "professor")
        self.admin = make_user("admin@uem.br", "admin")

    def login(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")


    def test_requires_authentication(self):
        resp = self.client.get("/api/avisos/")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["code"], "not_authenticated")







    def test_list_order_and_filter(self):
        Aviso.objects.create(titulo="normal", conteudo=".", autor=self.prof)
        Aviso.objects.create(titulo="urgente", conteudo=".", prioridade="alta", categoria="alerta", autor=self.prof)
        Aviso.objects.create(titulo="mais novo", conteudo=".", autor=self.prof)
        self.login(self.aluno)
        titulos = [a["titulo"] for a in self.client.get("/api/avisos/").json()["results"]]
        self.assertEqual(titulos, ["urgente", "mais novo", "normal"])
        self.assertEqual(len(self.client.get("/api/avisos/?categoria=alerta").json()["results"]), 1)

    def test_pagination(self):
        Aviso.objects.bulk_create(Aviso(titulo=f"a{i}", conteudo=".", autor=self.prof) for i in range(55))
        self.login(self.aluno)
        page = self.client.get("/api/avisos/").json()
        self.assertEqual((page["count"], len(page["results"])), (55, 20))
        self.assertIsNotNone(page["next"])
        self.assertEqual(len(self.client.get("/api/avisos/?limit=100000").json()["results"]), 50)  # max_limit
        last = self.client.get("/api/avisos/?offset=50").json()
        self.assertEqual((len(last["results"]), last["next"]), (5, None))

