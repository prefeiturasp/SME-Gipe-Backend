import uuid
import pytest
from unittest.mock import patch
from django.http import Http404
from django.utils.timezone import now, timedelta

from apps.users.models import User
from apps.alteracao_email.models.alteracao_email import AlteracaoEmail
from apps.helpers.exceptions import TokenJaUtilizadoException, TokenExpiradoException
from apps.alteracao_email.services.alteracao_email_service import AlteracaoEmailService


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="teste",
        email="usuario@sme.prefeitura.sp.gov.br",
        password="senha123",
        cpf="12345678900",
        name="Usuário Teste",
    )


@pytest.mark.django_db
class TestSolicitar:

    def test_solicitar_sucesso(self, user):

        with patch("apps.alteracao_email.services.alteracao_email_service.EnviaEmailService.enviar") as mock_enviar:
            email_request = AlteracaoEmailService.solicitar(user, "novo@sme.prefeitura.sp.gov.br")

        assert AlteracaoEmail.objects.count() == 1
        assert email_request.novo_email == "novo@sme.prefeitura.sp.gov.br"
        
        mock_enviar.assert_called_once()
        _, kwargs = mock_enviar.call_args

        assert kwargs["destinatario"] == "novo@sme.prefeitura.sp.gov.br"
        assert "alteracao_email.html" in kwargs["template_html"]


@pytest.mark.django_db
class TestValidar:

    def test_validar_sucesso(self, user):

        email_request = AlteracaoEmail.objects.create(
            usuario=user,
            novo_email="novo@sme.prefeitura.sp.gov.br",
        )

        usuario = AlteracaoEmailService.validar(email_request.token)

        user.refresh_from_db()
        email_request.refresh_from_db()

        assert usuario.email == "novo@sme.prefeitura.sp.gov.br"
        assert email_request.ja_usado is True

    def test_validar_token_ja_usado(self, user):

        email_request = AlteracaoEmail.objects.create(
            usuario=user,
            novo_email="novo@sme.prefeitura.sp.gov.br",
            ja_usado=True,
        )

        with pytest.raises(TokenJaUtilizadoException):
            AlteracaoEmailService.validar(email_request.token)

    def test_validar_token_expirado(self, user):

        email_request = AlteracaoEmail.objects.create(
            usuario=user,
            novo_email="novo@sme.prefeitura.sp.gov.br",
        )
        email_request.criado_em = now() - timedelta(minutes=31)
        email_request.save(update_fields=["criado_em"])

        with pytest.raises(TokenExpiradoException):
            AlteracaoEmailService.validar(email_request.token)

    def test_validar_token_inexistente(self):

        token_inexistente = uuid.uuid4()

        with pytest.raises(Http404):
            AlteracaoEmailService.validar(token_inexistente)