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

    def post_aviso(self, **extra):
        data = {"titulo": "Prova", "conteudo": "Sexta", "categoria": "prazo", **extra}
        return self.client.post("/api/avisos/", data, format="multipart")

    def test_requires_authentication(self):
        resp = self.client.get("/api/avisos/")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["code"], "not_authenticated")

    def test_aluno_cannot_post(self):
        self.login(self.aluno)
        resp = self.post_aviso()
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], "permission_denied")

    def test_professor_posts_with_and_without_attachment(self):
        self.login(self.prof)
        resp = self.client.post("/api/avisos/", {"titulo": "A", "conteudo": "B"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.json()["anexo"])
        self.assertEqual(resp.json()["autor"], {"id": self.prof.id, "name": "prof", "role": "professor"})

        resp = self.post_aviso(anexo=SimpleUploadedFile("edital.pdf", b"%PDF-1.4 ok", "application/pdf"))
        self.assertEqual(resp.status_code, 201)
        self.assertRegex(resp.json()["anexo"], r"^/media/anexos/[0-9a-f]{32}\.pdf$")

    def test_attachment_validation(self):
        self.login(self.prof)
        resp = self.post_aviso(anexo=SimpleUploadedFile("virus.exe", b"MZ", "application/octet-stream"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("anexo", resp.json())
        big = SimpleUploadedFile("grande.pdf", b"0" * (5 * 1024 * 1024 + 1), "application/pdf")
        resp = self.post_aviso(anexo=big)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("anexo", resp.json())

    def test_attachment_content_must_match_extension(self):
        self.login(self.prof)
        disfarcado = SimpleUploadedFile("foto.png", b"<html><script>alert(1)</script>", "image/png")
        resp = self.post_aviso(anexo=disfarcado)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("anexo", resp.json())
        jpg = SimpleUploadedFile("foto.JPG", b"\xff\xd8\xff\xe0 jfif", "image/jpeg")
        self.assertEqual(self.post_aviso(anexo=jpg).status_code, 201)

    def test_deleting_aviso_removes_attachment(self):
        self.login(self.prof)
        pdf = SimpleUploadedFile("edital.pdf", b"%PDF-1.4 ok", "application/pdf")
        aviso = Aviso.objects.get(pk=self.post_aviso(anexo=pdf).json()["id"])
        storage, name = aviso.anexo.storage, aviso.anexo.name
        self.assertTrue(storage.exists(name))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete(f"/api/avisos/{aviso.id}/").status_code, 204)
        self.assertFalse(storage.exists(name))

    def test_publication_is_throttled_per_user(self):
        self.login(self.prof2)
        for _ in range(30):
            self.assertEqual(self.client.post("/api/avisos/", {"titulo": "A", "conteudo": "B"}, format="json").status_code, 201)
        resp = self.client.post("/api/avisos/", {"titulo": "A", "conteudo": "B"}, format="json")
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.json()["code"], "throttled")
        self.assertEqual(self.client.get("/api/avisos/").status_code, 200)  # leitura não é limitada

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

    def test_delete_only_autor_or_admin(self):
        aviso = Aviso.objects.create(titulo="x", conteudo=".", autor=self.prof)
        self.login(self.prof2)
        self.assertEqual(self.client.delete(f"/api/avisos/{aviso.id}/").status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.client.delete(f"/api/avisos/{aviso.id}/").status_code, 204)
