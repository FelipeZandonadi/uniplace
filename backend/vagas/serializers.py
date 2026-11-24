from rest_framework import serializers

from accounts.models import User
from accounts.serializers import AutorSerializer

from .models import Candidatura, Vaga


class VagaSerializer(serializers.ModelSerializer):
    autor = AutorSerializer(read_only=True)
    ja_candidatou = serializers.SerializerMethodField()

    class Meta:
        model = Vaga
        fields = ["id", "titulo", "descricao", "tipo", "curso", "prazo", "aberta", "autor", "ja_candidatou", "created_at"]

    def get_ja_candidatou(self, obj) -> bool:
        return getattr(obj, "ja_candidatou", False)  # anotado com Exists() no queryset


class VagaResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vaga
        fields = ["id", "titulo", "tipo"]


class AlunoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "ra", "course"]


class CandidaturaSerializer(serializers.ModelSerializer):
    vaga = VagaResumoSerializer(read_only=True)
    aluno = AlunoSerializer(read_only=True)

    class Meta:
        model = Candidatura
        fields = ["id", "vaga", "aluno", "mensagem", "status", "created_at"]
        read_only_fields = ["status"]


class CandidaturaStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidatura
        fields = ["status"]
        extra_kwargs = {"status": {"required": True}}
