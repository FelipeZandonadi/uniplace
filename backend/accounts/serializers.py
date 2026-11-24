from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "ra", "role", "course"]


class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "role"]


class ErroSerializer(serializers.Serializer):
    """Só para a documentação (Swagger): formato padrão de erro do contrato."""

    detail = serializers.CharField()
    code = serializers.CharField()


def erro(descricao):
    return OpenApiResponse(ErroSerializer, description=descricao)
