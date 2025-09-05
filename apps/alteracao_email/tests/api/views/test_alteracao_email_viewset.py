import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.alteracao_email.services.alteracao_email_service import (
    AlteracaoEmailService,
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