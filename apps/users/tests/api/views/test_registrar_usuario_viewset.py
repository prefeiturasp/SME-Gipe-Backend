import pytest
from unittest.mock import patch

from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Cargo, User
from apps.unidades.models.unidades import Unidade, TipoGestaoChoices


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def unidade():
    return Unidade.objects.create(nome="Unidade Teste")


@pytest.fixture
def cargo():
    return Cargo.objects.create(codigo=1234, nome="Gestor")


@pytest.fixture
def valid_payload(unidade, cargo):
    return {
        "username": "usuarioapi",
        "password": "senha123",
        "name": "Usuário API",
        "email": "api@sme.prefeitura.sp.gov.br",
        "cpf": "98765432100",
        "cargo": cargo.pk,
        "unidades": [unidade.uuid],
        "rede": TipoGestaoChoices.DIRETA,
    }


@pytest.mark.django_db
class TestUserCreateView:

    endpoint = "/api/users/registrar"

    def test_user_created_successfully(self, client, valid_payload):

        response = client.post(self.endpoint, data=valid_payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username="usuarioapi").exists()

    def test_validation_error_returns_400(self, client, valid_payload):

        valid_payload["cpf"] = "123"
        response = client.post(self.endpoint, data=valid_payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["field"] == "cpf"
        assert response.data["detail"] == "CPF inválido."

    def test_duplicate_username_returns_400(self, client, valid_payload):

        User.objects.create_user(
            username=valid_payload["username"],
            password="senha123",
            name="Já existe",
            email="outro@sme.prefeitura.sp.gov.br",
            cpf="11122233344",
            cargo_id=valid_payload["cargo"],
            rede=valid_payload["rede"]
        )
        response = client.post(self.endpoint, data=valid_payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["field"] == "username"
        assert response.data["detail"] == "Este usuário já está cadastrado."

    def test_internal_server_error_returns_500(self, client, valid_payload):

        with patch("apps.users.api.serializers.registrar_usuario_serializer.UserCreateSerializer.save", side_effect=Exception("Erro simulado")):
            response = client.post(self.endpoint, data=valid_payload, format="json")

            assert response.status_code == 500
            assert response.data["detail"] == "Erro interno ao criar usuário."
            assert "Erro simulado" in response.data["detalhes"]