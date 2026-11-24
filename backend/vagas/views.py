from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.exceptions import ApiError
from accounts.permissions import HasRole, IsOwnerOrAdmin
from accounts.serializers import erro

from .models import Candidatura, Vaga
from .serializers import CandidaturaSerializer, CandidaturaStatusSerializer, VagaSerializer


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
        qs = Vaga.objects.select_related("autor").annotate(
            ja_candidatou=Exists(Candidatura.objects.filter(vaga=OuterRef("pk"), aluno=user))
        )
        if user.role == "aluno":
            qs = qs.filter(Q(curso="") | Q(curso=user.course))
            if self.action == "list":  # candidatar em vaga fechada deve dar 400 vaga_fechada, não 404
                qs = qs.filter(aberta=True, prazo__gte=timezone.localdate())
        tipo = self.request.query_params.get("tipo")
        return qs.filter(tipo=tipo) if tipo else qs

    def get_permissions(self):
        if self.action == "create":
            return [HasRole("colaborador", "admin")]
        if self.action == "candidatar":
            return [HasRole("aluno")]
        if self.action in ("partial_update", "candidaturas"):
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

    @extend_schema(
        summary="Candidatar-se (aluno)", request=CandidaturaSerializer,
        responses={
            201: CandidaturaSerializer,
            400: erro("`vaga_fechada` (fechada ou prazo vencido)"),
            403: erro("Apenas alunos"),
            404: erro("Vaga inexistente ou de outro curso"),
            409: erro("`already_applied`"),
        },
    )
    @action(detail=True, methods=["post"])
    def candidatar(self, request, pk=None):
        vaga = self.get_object()  # 404 se o aluno não pode ver a vaga (outro curso/fechada)
        if not vaga.aberta or vaga.prazo < timezone.localdate():
            raise ApiError(400, "Esta vaga não está mais aberta para candidaturas.", "vaga_fechada")
        serializer = CandidaturaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save(vaga=vaga, aluno=request.user)
        except IntegrityError:  # UniqueConstraint(vaga, aluno) no banco
            raise ApiError(409, "Você já se candidatou a esta vaga.", "already_applied")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Candidaturas"], summary="Candidaturas recebidas pela vaga (autor ou admin)",
        responses={200: CandidaturaSerializer(many=True), 403: erro("Apenas o autor da vaga ou admin")},
    )
    @action(detail=True, methods=["get"])
    def candidaturas(self, request, pk=None):
        vaga = self.get_object()
        page = self.paginate_queryset(vaga.candidaturas.select_related("vaga", "aluno"))
        return self.get_paginated_response(CandidaturaSerializer(page, many=True).data)


@extend_schema(tags=["Candidaturas"])
class CandidaturaViewSet(viewsets.GenericViewSet):
    queryset = Candidatura.objects.select_related("vaga", "aluno")
    serializer_class = CandidaturaSerializer

    def get_permissions(self):
        if self.action == "minhas":
            return [HasRole("aluno")]
        return [IsAuthenticated(), IsOwnerOrAdmin(lambda c: c.vaga.autor_id)]

    @extend_schema(summary="Minhas candidaturas (aluno)", responses=CandidaturaSerializer(many=True))
    @action(detail=False, methods=["get"])
    def minhas(self, request):
        page = self.paginate_queryset(self.get_queryset().filter(aluno=request.user))
        return self.get_paginated_response(CandidaturaSerializer(page, many=True).data)

    @extend_schema(
        summary="Alterar status da candidatura (autor da vaga ou admin)",
        request=CandidaturaStatusSerializer,
        responses={200: CandidaturaSerializer, 403: erro("Apenas o autor da vaga ou admin")},
    )
    def partial_update(self, request, pk=None):
        candidatura = self.get_object()
        serializer = CandidaturaStatusSerializer(candidatura, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CandidaturaSerializer(candidatura).data)
