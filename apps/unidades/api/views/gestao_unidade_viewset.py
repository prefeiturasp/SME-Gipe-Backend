from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django.http import Http404
from rest_framework.exceptions import ValidationError

from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices
from apps.unidades.api.serializers.gestao_unidade_serializer import (
    GestaoUnidadeSerializer,
    GestaoUnidadeListaSerializer,
)
from apps.unidades.services.gestao_unidade_service import InativarUnidadeService, ReativarUnidadeService

class GestaoUnidadeViewSet(ModelViewSet):

    queryset = Unidade.objects.select_related("dre").order_by("nome")
    lookup_field = "uuid"

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise ValidationError({"detail": "Unidade informada não existe."})
    
    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return GestaoUnidadeListaSerializer
        return GestaoUnidadeSerializer

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        
        qs = self.queryset

        if user.is_gipe:
            base_qs = qs

        elif user.is_ponto_focal:

            dres_pf = user.unidades.filter(
                tipo_unidade=TipoUnidadeChoices.DRE
            ).values_list("uuid", flat=True)

            # Retorna as DREs do ponto focal OU unidades subordinadas a essas DREs
            base_qs = qs.filter(
                Q(uuid__in=dres_pf) | Q(dre__uuid__in=dres_pf)
            ).distinct()

        else:
            base_qs = qs.none()
            
         # Filtros
        tipo = params.get("tipo_unidade")
        if tipo:
            base_qs = base_qs.filter(tipo_unidade=tipo)
            
        dre_uuid = params.get("dre")
        if dre_uuid:
            base_qs = base_qs.filter(dre__uuid=dre_uuid)

        rede = params.get("rede")
        if rede:
            base_qs = base_qs.filter(rede=rede)

        ativa = params.get("ativa")
        if ativa is not None:
            ativa_bool = str(ativa).lower() in ["true", "1", "t", "yes", "sim"]
            base_qs = base_qs.filter(ativa=ativa_bool)

        return base_qs

    @action(detail=True, methods=["post"], url_path="inativar")
    def inativar(self, request, uuid=None):
        unidade = self.get_object()
        motivo_inativacao = request.data.get("motivo_inativacao")

        if not motivo_inativacao:
            return Response(
                {"detail": "Motivo inativação é obrigatória para executar a inativação."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        InativarUnidadeService(
            unidade=unidade,
            usuario_responsavel=str(request.user),
            motivo_inativacao=motivo_inativacao
        ).executar()

        return Response(
            {"detail": "Unidade e usuários inativados com sucesso."},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["post"], url_path="reativar")
    def reativar(self, request, uuid=None):
        unidade = self.get_object()

        motivo_reativacao = request.data.get("motivo_reativacao")
        if not motivo_reativacao:
            return Response(
                {"detail": "O motivo da reativação é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ReativarUnidadeService(
            unidade=unidade,
            usuario_responsavel=str(request.user),
            motivo_reativacao=motivo_reativacao,
        )
        service.executar()

        return Response(
            {"detail": "Unidade reativada com sucesso."},
            status=status.HTTP_200_OK,
        )
        
    @action(detail=False, methods=['get'], url_path='tipos-unidade')
    def tipos_unidade(self, _):
        tipos = [{"id": choice[0], "label": choice[1]} for choice in TipoUnidadeChoices.choices]
        return Response(tipos, status=status.HTTP_200_OK)