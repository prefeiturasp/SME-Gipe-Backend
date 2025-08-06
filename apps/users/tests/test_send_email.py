import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from unittest.mock import patch
from apps.users.services.send_email import send_email_service


@pytest.fixture(autouse=True)
def use_locmem_email_backend(settings):
    # Configura backend de email para evitar envios reais durante os testes
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


@pytest.mark.django_db
class TestSendEmailService:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def email_data(self):
        return {
            "destinatario": "test@example.com",
            "assunto": "Teste de envio 03",
            "template_html": "emails/exemplo.html",
            "contexto": {"nome": "Usuário Teste"},
        }

    def test_send_email_success(self, email_data):
        # Limpa a outbox antes
        mail.outbox = []

        send_email_service(**email_data)

        # Verifica que 1 email foi "enviado"
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.subject == email_data['assunto']
        assert email.to == [email_data['destinatario']]
        assert 'Usuário Teste' in email.body

    def test_send_email_empty_destinatario_raises(self, email_data):
        email_data['destinatario'] = ''
        with pytest.raises(ValidationError):
            send_email_service(**email_data)

    def test_send_email_empty_assunto_raises(self, email_data):
        email_data['assunto'] = ''
        with pytest.raises(ValidationError):
            send_email_service(**email_data)

    def test_send_email_unexpected_exception_raises_runtimeerror(self, email_data):
        # Patch no método email.send para lançar uma exceção genérica
        with patch('django.core.mail.EmailMessage.send', side_effect=Exception("Erro inesperado")):
            with pytest.raises(RuntimeError, match="Erro inesperado ao enviar e-mail."):
                send_email_service(**email_data)