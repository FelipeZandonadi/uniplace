from rest_framework import serializers

from accounts.serializers import AutorSerializer

from .models import Aviso

class AvisoSerializer(serializers.ModelSerializer):
    autor = AutorSerializer(read_only=True)

    class Meta:
        model = Aviso
        fields = ["id", "titulo", "conteudo", "categoria", "prioridade", "anexo", "autor", "created_at"]

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["anexo"] = obj.anexo.url if obj.anexo else None  # contrato: caminho relativo /media/...
        return data
