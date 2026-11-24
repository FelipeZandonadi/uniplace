from rest_framework import serializers

from accounts.serializers import AutorSerializer

from .models import Vaga


class VagaSerializer(serializers.ModelSerializer):
    autor = AutorSerializer(read_only=True)
    ja_candidatou = serializers.SerializerMethodField()

    class Meta:
        model = Vaga
        fields = ["id", "titulo", "descricao", "tipo", "curso", "prazo", "aberta", "autor", "ja_candidatou", "created_at"]

    def get_ja_candidatou(self, obj) -> bool:
        return getattr(obj, "ja_candidatou", False)  # anotado com Exists() no queryset
