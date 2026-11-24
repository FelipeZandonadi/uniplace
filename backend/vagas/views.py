from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from accounts.permissions import HasRole, IsOwnerOrAdmin
from accounts.serializers import erro

from .models import Vaga
from .serializers import VagaSerializer


@extend_schema(tags=["Vagas"])
@extend_schema_view(
    list=extend_schema(
        summary="Listar vagas (aluno: só abertas, no prazo e do seu curso ou de qualquer curso)",
        parameters=[OpenApiParameter("tipo", enum=Vaga.Tipo.values)],
    ),
    create=extend_schema(summary="Publicar vaga (colaborador, admin)", responses={201: VagaSerializer, 403: erro("Perfil sem permissão")}),
    partial_update=extend_schema(summary="Editar vaga, ex.: {\"aberta\": false} (autor ou admin)"),
)
class VagaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = VagaSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    throttle_scope = "publicacao"

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.action == "create" else []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # geração do schema do Swagger: sem usuário real
            return Vaga.objects.none()
        user = self.request.user
        qs = Vaga.objects.select_related("autor")
        if user.role == "aluno":
            qs = qs.filter(Q(curso="") | Q(curso=user.course))
            if self.action == "list":
                qs = qs.filter(aberta=True, prazo__gte=timezone.localdate())
        tipo = self.request.query_params.get("tipo")
        return qs.filter(tipo=tipo) if tipo else qs

    def get_permissions(self):
        if self.action == "create":
            return [HasRole("colaborador", "admin")]
        if self.action == "partial_update":
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)


