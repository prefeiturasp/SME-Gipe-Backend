import logging

from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from apps.users.models import User
from apps.users.permissions import IsInternalServiceRequest
from apps.users.services.envia_email_service import EnviaEmailService

logger = logging.getLogger(__name__)


class CargoEnum:
    GIPE = 0
    PONTO_FOCAL_DRE = 1
    ASSISTENTE_DE_DIRETOR_DE_ESCOLA = 3085
    DIRETOR_DE_ESCOLA = 3360


class IntercorrenciaViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [IsInternalServiceRequest]

    @action(detail=False, methods=["post"], url_path="alerta-finalizacao-ocorrencia")
    def alerta_finalizacao_ocorrencia(self, request):

        data = request.data

        username = (data.get("username") or "").strip()
        data_ocorrencia = data.get("data_ocorrencia")
        uuid_ocorrencia = data.get("uuid_ocorrencia")

        logger.info(
            "Recebida solicitação de envio de e-mail de finalização",
            extra={
                "username": username,
                "uuid_ocorrencia": uuid_ocorrencia,
            },
        )

        if not username or not data_ocorrencia or not uuid_ocorrencia:
            logger.info(
                "Payload inválido para envio de e-mail",
                extra={
                    "username": username,
                    "uuid_ocorrencia": uuid_ocorrencia,
                },
            )
            return Response(
                {
                    "success": False,
                    "error": "Campos obrigatórios: username, data_ocorrencia, uuid_ocorrencia",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = (
            User.objects
            .filter(username=username)
            .only("email", "cargo")
            .first()
        )            

        if not user or not user.email:
            logger.info(
                "Usuário não encontrado ou sem e-mail",
                extra={
                    "username": username,
                },
            )
            return Response(
                {"success": False, "error": "Usuário não encontrado ou sem e-mail"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if user.cargo.codigo == CargoEnum.GIPE:
            logger.info(
                "Usuário é GIPE, não é necessário enviar e-mail",
                extra={
                    "username": username,
                },
            )
            return Response(
                {"success": True, "message": "Usuário é GIPE, não é necessário enviar e-mail"},
                status=status.HTTP_200_OK,
            )

        destinatario = user.email

        contexto = {
            "texto": "vinculada à sua DRE" if user.cargo.codigo == CargoEnum.PONTO_FOCAL_DRE else "por sua Unidade Educacional",
            "data_ocorrencia": data_ocorrencia,
            "url_action": f"{settings.FRONTEND_URL}/dashboard/cadastrar-ocorrencia/{uuid_ocorrencia}",
        }

        try:
            logger.info(
                "Enviando e-mail de finalização",
                extra={
                    "destinatario": destinatario,
                    "username": username,
                    "uuid_ocorrencia": uuid_ocorrencia,
                },
            )

            EnviaEmailService.enviar(
                destinatario=destinatario,
                assunto="Intercorrência finalizada pelo GIPE",
                template_html="emails/finalizacao_intercorrencia.html",
                contexto=contexto,
            )

            logger.info(
                "E-mail enviado com sucesso",
                extra={
                    "destinatario": destinatario,
                    "username": username,
                    "uuid_ocorrencia": uuid_ocorrencia,
                },
            )

            return Response({"success": True}, status=status.HTTP_200_OK)

        except Exception:
            logger.exception(
                "Erro ao enviar e-mail de finalização",
                extra={
                    "destinatario": destinatario,
                    "username": username,
                    "uuid_ocorrencia": uuid_ocorrencia,
                },
            )

            return Response(
                {"success": False, "error": "Erro interno ao enviar e-mail"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )