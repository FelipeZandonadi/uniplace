from django.conf import settings
from django.db import models


class Vaga(models.Model):
    class Tipo(models.TextChoices):
        ESTAGIO = "estagio", "Estágio"
        BOLSA = "bolsa", "Bolsa"
        MONITORIA = "monitoria", "Monitoria"

    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    curso = models.CharField(max_length=120, blank=True)  # vazio = qualquer curso
    prazo = models.DateField()
    aberta = models.BooleanField(default=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vagas")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.titulo


class Candidatura(models.Model):
    class Status(models.TextChoices):
        ENVIADA = "enviada", "Enviada"
        EM_ANALISE = "em_analise", "Em análise"
        APROVADA = "aprovada", "Aprovada"
        RECUSADA = "recusada", "Recusada"

    vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, related_name="candidaturas")
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidaturas")
    mensagem = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ENVIADA)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["vaga", "aluno"], name="uniq_candidatura_vaga_aluno")]

    def __str__(self):
        return f"{self.aluno} -> {self.vaga}"
