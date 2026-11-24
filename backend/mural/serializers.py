from pathlib import Path

from rest_framework import serializers

from accounts.serializers import AutorSerializer

from .models import Aviso

# Magic bytes por extensão: a extensão e o MIME vêm do cliente; o cabeçalho do arquivo, não.
ASSINATURAS = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff"}


class AvisoSerializer(serializers.ModelSerializer):
    autor = AutorSerializer(read_only=True)

    class Meta:
        model = Aviso
        fields = ["id", "titulo", "conteudo", "categoria", "prioridade", "anexo", "autor", "created_at"]

    def validate_anexo(self, arquivo):
        # Roda depois dos validadores do model (extensão e tamanho já conferidos).
        if not arquivo:
            return arquivo
        assinatura = ASSINATURAS.get(Path(arquivo.name).suffix.lower(), b"")
        cabecalho = arquivo.read(len(assinatura))
        arquivo.seek(0)
        if not assinatura or cabecalho != assinatura:
            raise serializers.ValidationError("O conteúdo do arquivo não corresponde a um PDF, PNG ou JPG.")
        return arquivo

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["anexo"] = obj.anexo.url if obj.anexo else None  # contrato: caminho relativo /media/...
        return data
