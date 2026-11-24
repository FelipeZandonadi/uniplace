from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Aviso
from .serializers import AvisoSerializer


@extend_schema(tags=["Mural"])
@extend_schema_view(
    list=extend_schema(
        summary="Listar avisos (prioridade alta primeiro, depois mais recentes)",
        parameters=[OpenApiParameter("categoria", enum=Aviso.Categoria.values)],
    ),
)
class AvisoViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AvisoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Aviso.objects.select_related("autor")
        categoria = self.request.query_params.get("categoria")
        return qs.filter(categoria=categoria) if categoria else qs
