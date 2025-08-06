import logging
from django.core.mail import EmailMessage, BadHeaderError
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def send_email_service(destinatario, assunto, template_html, contexto):
    """Envia e-mail HTML usando apenas os recursos padrão do Django."""

    try:
        if not destinatario:
            raise ValidationError("Destinatário não pode ser vazio.")
        if not assunto:
            raise ValidationError("Assunto não pode ser vazio.")

        corpo_html = render_to_string(template_html, contexto)

        email = EmailMessage(
            subject=assunto,
            body=corpo_html,
            to=[destinatario] if isinstance(destinatario, str) else destinatario,
        )
        email.content_subtype = 'html'
        email.send()

        logger.info(f"E-mail enviado com sucesso para {destinatario} usando o template '{template_html}'.")

    except (ValidationError, BadHeaderError) as e:
        logger.error(f"Erro ao enviar e-mail: {str(e)}")
        raise

    except Exception as e:
        logger.exception("Erro inesperado ao enviar e-mail.")
        raise RuntimeError("Erro inesperado ao enviar e-mail.") from e