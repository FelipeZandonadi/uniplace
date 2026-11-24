from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from accounts.permissions import HasRole, IsOwnerOrAdmin
from accounts.serializers import erro

from .models import Aviso
from .serializers import AvisoSerializer


@extend_schema(tags=["Mural"])
@extend_schema_view(
    list=extend_schema(
        summary="Listar avisos (prioridade alta primeiro, depois mais recentes)",
        parameters=[OpenApiParameter("categoria", enum=Aviso.Categoria.values)],
    ),
    create=extend_schema(
        summary="Publicar aviso (professor, colaborador, admin)",
        description="Envie `multipart/form-data` para incluir `anexo` (pdf/png/jpg, até 5 MB) ou JSON sem anexo.",
        request={"multipart/form-data": AvisoSerializer, "application/json": AvisoSerializer},
        responses={201: AvisoSerializer, 403: erro("Perfil sem permissão (ex.: aluno)")},
    ),
    destroy=extend_schema(summary="Remover aviso (autor ou admin)", responses={204: None, 403: erro("Apenas autor ou admin")}),
)
class AvisoViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = AvisoSerializer
    throttle_scope = "publicacao"

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.action == "create" else []

    def get_queryset(self):
        qs = Aviso.objects.select_related("autor")
        categoria = self.request.query_params.get("categoria")
        return qs.filter(categoria=categoria) if categoria else qs

    def get_permissions(self):
        if self.action == "create":
            return [HasRole("professor", "colaborador", "admin")]
        if self.action == "destroy":
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
