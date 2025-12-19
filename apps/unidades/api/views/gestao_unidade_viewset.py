from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices
from apps.unidades.api.serializers.gestao_unidade_serializer import (
    GestaoUnidadeSerializer,
    GestaoUnidadeListaSerializer,
)


class GestaoUnidadeViewSet(ModelViewSet):

    queryset = Unidade.objects.select_related("dre").order_by("nome")
    lookup_field = "uuid"
    
    def get_serializer_class(self):
        if self.action == "list" or self.action == "retrieve":
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

            base_qs = qs.filter(dre__uuid__in=dres_pf).distinct()

        else:
            base_qs = qs.none()
            
         # Filtros
        dre_uuid = params.get("dre")
        if dre_uuid:
            base_qs = base_qs.filter(dre__uuid=dre_uuid)

        rede = params.get("rede")
        if rede:
            base_qs = base_qs.filter(rede=rede)

        tipo = params.get("tipo_unidade")
        if tipo:
            base_qs = base_qs.filter(tipo_unidade=tipo)

        ativa = params.get("ativa")
        if ativa is not None:
            ativa_bool = str(ativa).lower() in ["true", "1", "t", "yes", "sim"]
            base_qs = base_qs.filter(ativa=ativa_bool)

        return base_qs

    @action(detail=True, methods=["post"], url_path="ativar")
    def ativar(self, request, uuid=None):
        unidade = self.get_object()
        unidade.ativa = True
        unidade.save(update_fields=["ativa"])
        return Response(
            {"detail": "Unidade ativada com sucesso."}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"], url_path="inativar")
    def inativar(self, request, uuid=None):
        unidade = self.get_object()
        unidade.ativa = False
        unidade.save(update_fields=["ativa"])
        return Response(
            {"detail": "Unidade inativada com sucesso."}, status=status.HTTP_200_OK
        )
        
    @action(detail=False, methods=['get'], url_path='tipos-unidade')
    def tipos_unidade(self, _):
        tipos = [{"id": choice[0], "label": choice[1]} for choice in TipoUnidadeChoices.choices]
        return Response(tipos, status=status.HTTP_200_OK)