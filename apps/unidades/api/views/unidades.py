import uuid
import logging

from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.unidades.api.serializers.unidades import UnidadeSerializer
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices, TipoGestaoChoices

logger = logging.getLogger(__name__)


class UnidadeViewSet(ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = UnidadeSerializer
    queryset = Unidade.objects.all()

    def list(self, request, *args, **kwargs):
        tipo = request.query_params.get("tipo")
        codigo_dre = request.query_params.get("dre")

        logger.info("Listagem de unidades solicitada com tipo='%s' e dre='%s'", tipo, codigo_dre)

        if tipo == "DRE":
            return self._listar_dres()

        if tipo == "UE":
            return self._listar_ues(codigo_dre)

        if tipo is None:
            logger.info("Nenhum parâmetro 'tipo' informado. Retornando todas as unidades.")
            return super().list(request, *args, **kwargs)

        logger.warning("Parâmetro 'tipo' inválido recebido: %s", tipo)
        return self._resposta_erro(
            "Parâmetro 'tipo' inválido. Use 'DRE', 'UE' ou não informe para listar todos.",
            status.HTTP_400_BAD_REQUEST
        )

    def _listar_dres(self):
        unidades = self.queryset.filter(tipo_unidade=TipoUnidadeChoices.DRE).order_by("tipo_unidade", "nome")
        logger.info("Filtrando unidades do tipo DRE. Quantidade encontrada: %d", unidades.count())
        return self._responder_com_serializador(unidades)

    def _listar_ues(self, codigo_dre):
        if not codigo_dre:
            logger.warning("Parâmetro 'dre' não informado para tipo UE")
            return self._resposta_erro(
                "É necessário informar o código da DRE no parâmetro 'dre'.",
                status.HTTP_400_BAD_REQUEST
            )

        try:
            uuid_obj = uuid.UUID(codigo_dre)
        except ValueError:
            logger.warning("UUID inválido fornecido: %s", codigo_dre)
            return self._resposta_erro(
                "UUID inválido no parâmetro 'dre'.",
                status.HTTP_400_BAD_REQUEST
            )

        dre = get_object_or_404(
            Unidade,
            uuid=uuid_obj,
            tipo_unidade=TipoUnidadeChoices.DRE,
        )

        unidades = self.queryset.filter(
            dre=dre,
            rede=TipoGestaoChoices.INDIRETA
        ).order_by("tipo_unidade", "nome")
        
        logger.info("Filtrando UEs vinculadas à DRE uuid='%s'. Quantidade encontrada: %d", codigo_dre, unidades.count())

        return self._responder_com_serializador(unidades)

    def _responder_com_serializador(self, unidades):
        serializer = self.get_serializer(unidades, many=True)
        logger.info("Resposta serializada com %d unidades.", len(serializer.data))
        return Response(serializer.data)

    def _resposta_erro(self, mensagem, status_code):
        return Response({"detail": mensagem}, status=status_code)
    
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def verificar_unidade(self, request, pk=None):
        """ Verifica se a unidade pertence ao usuário autenticado """
        
        user = request.user
        unidade = self.get_object()

        if unidade in user.unidades.all():
            return Response(
                {"detail": "A unidade pertence ao usuário."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "A unidade não pertence ao usuário."},
            status=status.HTTP_403_FORBIDDEN
        )