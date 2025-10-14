import logging
import environ
from django.utils.timezone import now, timedelta
from django.shortcuts import get_object_or_404

from apps.alteracao_email.models.alteracao_email import AlteracaoEmail
from apps.users.services.envia_email_service import EnviaEmailService
from apps.helpers.exceptions import (
    TokenJaUtilizadoException,
    TokenExpiradoException,
)

env = environ.Env()
logger = logging.getLogger(__name__)


class AlteracaoEmailService:

    @staticmethod
    def solicitar(usuario, novo_email):
        
        email_request = AlteracaoEmail.objects.create(
            usuario=usuario,
            novo_email=novo_email
        )

        validation_link = f"{env('FRONTEND_URL')}/confirmar-email/{email_request.token}"
        logger.info(f"Link de validação gerado: {validation_link}")

        EnviaEmailService.enviar(
            destinatario=novo_email,
            assunto="Alteração de e-mail",
            template_html="emails/alteracao_email.html",
            contexto={"usuario_nome": usuario.name, "link": validation_link},
        )

        return email_request

    @staticmethod
    def validar(token):
        
        email_request = get_object_or_404(AlteracaoEmail, token=token)
        usuario = email_request.usuario

        if email_request.ja_usado:
            raise TokenJaUtilizadoException("Este token já foi utilizado.")

        if email_request.criado_em < now() - timedelta(minutes=30):
            raise TokenExpiradoException("Token expirado.")

        logger.info(f"E-mail alterado com sucesso: {usuario.email}")
        return usuario, email_request