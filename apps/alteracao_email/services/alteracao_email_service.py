import logging
import environ

from apps.users.services.envia_email_service import EnviaEmailService
from apps.alteracao_email.models.alteracao_email import AlteracaoEmail

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