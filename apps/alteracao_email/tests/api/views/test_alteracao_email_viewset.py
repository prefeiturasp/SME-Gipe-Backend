import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.alteracao_email.services.alteracao_email_service import (
    AlteracaoEmailService, AlteracaoEmail
)
from apps.helpers.exceptions import (
    TokenJaUtilizadoException,
    TokenExpiradoException,
    SmeIntegracaoException
)


@pytest.fixture
def api_client(db):
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="teste",
        email="usuario@sme.prefeitura.sp.gov.br",
        password="senha123",
        cpf="12345678900",
    )


@pytest.mark.django_db
class TestSolicitarAlteracaoEmailViewSet:

    endpoint = "/api/alteracao-email/solicitar/"

    def test_create_success(self, api_client, user):

        api_client.force_authenticate(user=user)
        payload = {"new_email": "novo@sme.prefeitura.sp.gov.br"}

        with patch.object(AlteracaoEmailService, "solicitar", return_value=None):
            response = api_client.post(self.endpoint, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "E-mail de confirmação enviado com sucesso."

    def test_create_erro_inesperado(self, api_client, user):

        api_client.force_authenticate(user=user)
        payload = {"new_email": "falha@sme.prefeitura.sp.gov.br"}

        with patch.object(
            AlteracaoEmailService,
            "solicitar",
            side_effect=Exception("Falha interna"),
        ):
            response = api_client.post(self.endpoint, payload, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["detail"] == "Erro inesperado."


@pytest.mark.django_db
class TestValidarAlteracaoEmailViewSet:

    endpoint = "/api/alteracao-email/validar/"

    @pytest.mark.django_db
    def test_update_success(self, api_client, user):
        api_client.force_authenticate(user=user)
        pk = "123"

        email_request = AlteracaoEmail.objects.create(
            usuario=user,
            novo_email="novo@sme.prefeitura.sp.gov.br",
        )

        with (
            patch.object(
                AlteracaoEmailService, "validar", return_value=(user, email_request)
            ),
            patch("apps.alteracao_email.api.views.alteracao_email_viewset.SmeIntegracaoService.altera_email") as mock_integracao,
        ):
            response = api_client.put(f"{self.endpoint}{pk}/")

        mock_integracao.assert_called_once_with(user.username, email_request.novo_email)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "E-mail alterado com sucesso."
        assert response.data["email"] == email_request.novo_email

        # confirma que os dados foram salvos
        user.refresh_from_db()
        email_request.refresh_from_db()
        assert user.email == email_request.novo_email
        assert email_request.ja_usado is True

    def test_update_token_ja_utilizado(self, api_client, user):

        api_client.force_authenticate(user=user)
        pk = "456"

        with patch.object(
            AlteracaoEmailService,
            "validar",
            side_effect=TokenJaUtilizadoException("Token já foi utilizado."),
        ):
            response = api_client.put(f"{self.endpoint}{pk}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token já foi utilizado." in response.data["detail"]

    def test_update_token_expirado(self, api_client, user):

        api_client.force_authenticate(user=user)
        pk = "789"

        with patch.object(
            AlteracaoEmailService,
            "validar",
            side_effect=TokenExpiradoException("Token expirado."),
        ):
            response = api_client.put(f"{self.endpoint}{pk}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token expirado." in response.data["detail"]

    def test_update_erro_inesperado(self, api_client, user):
        
        api_client.force_authenticate(user=user)
        pk = "000"

        with patch.object(
            AlteracaoEmailService,
            "validar",
            side_effect=Exception("Falha inesperada"),
        ):
            response = api_client.put(f"{self.endpoint}{pk}/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["detail"] == "Erro inesperado."

    @pytest.mark.django_db
    def test_update_integracao_falha(self, api_client, user, caplog):
        api_client.force_authenticate(user=user)
        pk = "123"

        email_request = AlteracaoEmail.objects.create(
            usuario=user,
            novo_email="novo@sme.prefeitura.sp.gov.br",
        )

        with (
            patch.object(
                AlteracaoEmailService, "validar", return_value=(user, email_request)
            ),
            patch(
                "apps.alteracao_email.api.views.alteracao_email_viewset.SmeIntegracaoService.altera_email",
                side_effect=SmeIntegracaoException("Falha na SME"),
            ) as mock_integracao,
        ):
            response = api_client.put(f"{self.endpoint}{pk}/")

        mock_integracao.assert_called_once_with(user.username, email_request.novo_email)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Falha na SME"

        assert any(
            "Erro na integração SME para alteração de email do usuário ID" in msg
            for msg in caplog.text.splitlines()
        )

