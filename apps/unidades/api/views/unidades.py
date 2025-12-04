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
        rede = request.query_params.get("rede")
        
        logger.info(
            "Listagem de unidades solicitada com tipo='%s', dre='%s' e rede='%s'",
            tipo, codigo_dre, rede
        )
 
        if tipo == "DRE":
            return self._listar_dres()
 
        if tipo == "UE":
            return self._listar_ues(codigo_dre, rede)
 
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
 
    def _listar_ues(self, codigo_dre, rede=None):
        """
        Lista Unidades Escolares vinculadas a uma DRE.
        
        Args:
            codigo_dre: UUID da DRE
            rede: Tipo de gestão da rede (DIRETA, INDIRETA ou None para todas)
                  Se não informado, mantém comportamento padrão (INDIRETA)
        """
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
 
        # Filtro base: unidades vinculadas à DRE
        unidades = self.queryset.filter(dre=dre)
        
        # Aplicar filtro de rede conforme parâmetro
        if rede is None:
            # Comportamento padrão: apenas INDIRETA (mantém compatibilidade)
            unidades = unidades.filter(rede=TipoGestaoChoices.INDIRETA)
            logger.info("Filtrando UEs INDIRETAS (padrão) da DRE uuid='%s'", codigo_dre)
        elif rede.upper() == "TODAS":
            # Retorna todas as redes
            logger.info("Filtrando TODAS as UEs da DRE uuid='%s'", codigo_dre)
        elif rede.upper() in [choice.value for choice in TipoGestaoChoices]:
            # Filtra por rede específica (DIRETA ou INDIRETA)
            unidades = unidades.filter(rede=rede.upper())
            logger.info("Filtrando UEs da rede '%s' da DRE uuid='%s'", rede.upper(), codigo_dre)
        else:
            # Rede inválida
            logger.warning("Parâmetro 'rede' inválido recebido: %s", rede)
            return self._resposta_erro(
                "Parâmetro 'rede' inválido. Use 'DIRETA', 'INDIRETA', 'TODAS' ou não informe para o padrão (INDIRETA).",
                status.HTTP_400_BAD_REQUEST
            )
        
        unidades = unidades.order_by("tipo_unidade", "nome")
        
        logger.info(
            "UEs vinculadas à DRE uuid='%s' (rede='%s'). Quantidade encontrada: %d",
            codigo_dre, rede or 'INDIRETA', unidades.count()
        )
        return self._responder_com_serializador(unidades)
 
    def _responder_com_serializador(self, unidades):
        serializer = self.get_serializer(unidades, many=True)
        logger.info("Resposta serializada com %d unidades.", len(serializer.data))
        return Response(serializer.data)
 
    def _resposta_erro(self, mensagem, status_code):
        return Response({"detail": mensagem}, status=status_code)
    
    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):

        codigos = request.data.get("codigos")

        if not isinstance(codigos, list):
            return Response(
                {"detail": "Campo 'codigos' deve ser uma lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unidades = Unidade.objects.filter(codigo_eol__in=codigos)
        serializer = UnidadeSerializer(unidades, many=True)

        resposta = {
            str(item["codigo_eol"]): item
            for item in serializer.data
        }

        return Response(resposta)