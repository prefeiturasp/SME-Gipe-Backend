import pytest
from unittest.mock import patch, MagicMock

from rest_framework.test import APIClient
from rest_framework import status, serializers

from apps.users.models import Cargo, User
from apps.unidades.models.unidades import Unidade, TipoGestaoChoices

from apps.users.api.views.usuario_viewset import (
    UserUpdateSerializer,
)

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

@pytest.fixture
def fake_user():
    """Usuário falso para simular request.user"""
    user = MagicMock()
    user.username = "jose.silva"
    user.name = "José Silva"
    return user


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
        assert response.data["detail"] == "Já existe uma conta com este CPF."

    def test_internal_server_error_returns_500(self, client, valid_payload):

        with patch("apps.users.api.serializers.usuario_serializer.UserCreateSerializer.save", side_effect=Exception("Erro simulado")):
            response = client.post(self.endpoint, data=valid_payload, format="json")

            assert response.status_code == 500
            assert response.data["detail"] == "Erro interno ao criar usuário."
            assert "Erro simulado" in response.data["detalhes"]

    def test_email_service_failure_logs_error(self, client, valid_payload, caplog):

        with patch("apps.users.services.envia_email_service.EnviaEmailService.enviar", side_effect=Exception("Erro no envio de e-mail")):
            response = client.post(self.endpoint, data=valid_payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username=valid_payload["username"]).exists()

        assert any("Falha ao enviar e-mail de confirmação" in rec.message for rec in caplog.records)


pytest.mark.django_db
class TestUserUpdateView:

    endpoint = "/api/users/atualizar-dados"

    def test_update_sucesso(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="usuarioapi",
            password="senha123",
            name="Nome Antigo"
        )
        client.force_authenticate(user=user)

        payload = {"name": "Nome Novo"}
        response = client.put(self.endpoint, data=payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Tudo certo por aqui!<br/>Seu nome foi atualizado."

        user.refresh_from_db()
        assert user.name == "Nome Novo"

    def test_update_com_numero(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="usuarioapi",
            password="senha123",
            name="Nome Antigo"
        )
        client.force_authenticate(user=user)

        payload = {"name": "Teste 1234"}
        response = client.put(self.endpoint, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["field"] == "name"
        assert response.data["detail"] == "O nome deve conter apenas letras e espaços."

    def test_update_sem_sobrenome(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="usuarioapi",
            password="senha123",
            name="Nome Antigo"
        )
        client.force_authenticate(user=user)

        payload = {"name": "Teste"}
        response = client.put(self.endpoint, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["field"] == "name"
        assert response.data["detail"] == "Digite seu nome completo (nome e sobrenome)."

    def test_serializer_raise_exception_true_line(self, client, django_user_model):
        """Teste para quando raise_exception igual a true"""

        user = django_user_model.objects.create_user(
            username="usuarioapi",
            password="senha123",
            name="Nome Antigo"
        )
        client.force_authenticate(user=user)

        payload = {"name": ""}

        serializer = UserUpdateSerializer(
            user, 
            data=payload,
            partial=True
        )

        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.is_valid(raise_exception=True)

        detail = exc_info.value.detail
        assert "detail" in detail
        assert "field" in detail

    def test_update_nome_em_branco(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="usuarioapi",
            password="senha123",
            name="Nome Antigo"
        )
        client.force_authenticate(user=user)

        payload = {"name": ""}
        response = client.put(self.endpoint, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["field"] == "name"
        assert response.data["detail"] == "Digite o seu nome completo."

    def test_internal_server_error_returns_500(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="usuarioapi",
            password="senha123",
            name="Nome Antigo"
        )
        client.force_authenticate(user=user)

        payload = {"name": "Nome Novo"}

        with patch("apps.users.api.serializers.usuario_serializer.UserUpdateSerializer.save",
                   side_effect=Exception("Erro simulado")):
            response = client.put(self.endpoint, data=payload, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["detail"] == "Erro interno do servidor."