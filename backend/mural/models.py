from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

MAX_ANEXO_BYTES = 5 * 1024 * 1024


def validate_anexo_size(file):
    if file.size > MAX_ANEXO_BYTES:
        raise ValidationError("O anexo deve ter no máximo 5 MB.")


def anexo_path(_instance, filename):
    return f"anexos/{uuid4().hex}{Path(filename).suffix.lower()}"


class Aviso(models.Model):
    class Categoria(models.TextChoices):
        AVISO = "aviso", "Aviso"
        PRAZO = "prazo", "Prazo"
        ALERTA = "alerta", "Alerta"
        EVENTO = "evento", "Evento"

    class Prioridade(models.TextChoices):
        ALTA = "alta", "Alta"
        NORMAL = "normal", "Normal"

    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    categoria = models.CharField(max_length=10, choices=Categoria.choices, default=Categoria.AVISO)
    prioridade = models.CharField(max_length=10, choices=Prioridade.choices, default=Prioridade.NORMAL)
    anexo = models.FileField(
        upload_to=anexo_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf", "png", "jpg", "jpeg"]), validate_anexo_size],
    )
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="avisos")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # "alta" < "normal" em ordem alfabética: prioridade alta primeiro, depois mais recentes.
        ordering = ["prioridade", "-created_at"]

    def __str__(self):
        return self.titulo


@receiver(post_delete, sender=Aviso)
def apagar_anexo(sender, instance, **kwargs):
    """Aviso removido (API, admin ou cascata do autor) não pode deixar o anexo acessível em /media/."""
    if instance.anexo:
        storage, name = instance.anexo.storage, instance.anexo.name
        transaction.on_commit(lambda: storage.delete(name))  # só apaga se a exclusão for confirmada
