import logging

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, BadHeaderError

logger = logging.getLogger(__name__)


class EnviaEmailService:
    """ Serviço para envio de e-mails HTML usando recursos padrão do Django. """

    @staticmethod
    def validar(destinatario, assunto):
        if not destinatario:
            raise ValidationError("Destinatário não pode ser vazio.")
        if not assunto:
            raise ValidationError("Assunto não pode ser vazio.")

    @staticmethod
    def renderizar_corpo(template_html, contexto):
        return render_to_string(template_html, contexto)

    @classmethod
    def enviar(cls, destinatario, assunto, template_html, contexto):
        """ Envia e-mail HTML sem necessidade de instanciar a classe. """

        try:
            cls.validar(destinatario, assunto)

            corpo_html = cls.renderizar_corpo(template_html, contexto)

            email = EmailMessage(
                subject=assunto,
                body=corpo_html,
                to=[destinatario] if isinstance(destinatario, str) else destinatario,
            )
            email.content_subtype = 'html'
            email.send()

            logger.info(
                f"E-mail enviado com sucesso para {destinatario} usando o template '{template_html}'."
            )

        except (ValidationError, BadHeaderError) as e:
            logger.error(f"Erro ao enviar e-mail: {str(e)}")
            raise

        except Exception as e:
            logger.exception("Erro inesperado ao enviar e-mail.")
            raise RuntimeError("Erro inesperado ao enviar e-mail.") from e