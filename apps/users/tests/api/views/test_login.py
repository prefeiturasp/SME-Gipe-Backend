import pytest
from rest_framework.test import APIRequestFactory
from rest_framework import status
from unittest.mock import patch, MagicMock
from apps.users.api.views.login import LoginView
from apps.helpers.exceptions import AuthenticationError, UserNotFoundError


class TestLoginView:

    @patch("apps.users.services.cargos.CargosService.get_cargo_permitido")
    @patch("apps.users.services.cargos.CargosService.get_cargos")
    @patch("apps.users.services.login.AutenticacaoService.autentica")
    def test_login_sucesso(self, mock_autentica, mock_get_cargos, mock_get_cargo_permitido):
        mock_autentica.return_value = {
            "nome": "João Silva",
            "email": "joao@email.com",
            "cpf": "12345678901",
            "login": "joaos",
            "visoes": []
        }

        mock_get_cargos.return_value = {"cargos": [{"codigo": 30, "nome": "Diretor de Escola"}]}
        mock_get_cargo_permitido.return_value = {"codigo": 30, "nome": "Diretor de Escola"}

        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "joaos", "password": "senha123"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "João Silva"
        assert response.data["cargo"]["codigo"] == 30

    def test_login_sem_credenciais(self):
        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "", "password": ""}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Login e senha são obrigatórios"

    @patch("apps.users.services.login.AutenticacaoService.autentica", side_effect=AuthenticationError("Credenciais inválidas"))
    def test_login_credenciais_invalidas(self, mock_autentica):
        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "usuario", "password": "senha_errada"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "Usuário e/ou senha inválida"

    @patch("apps.users.services.login.AutenticacaoService.autentica")
    @patch("apps.users.services.cargos.CargosService.get_cargos", side_effect=UserNotFoundError())
    def test_login_usuario_sem_cargo_permitido(self, mock_get_cargos, mock_autentica):
        mock_autentica.return_value = {
            "nome": "Maria Souza",
            "email": "maria@email.com",
            "cpf": "98765432100",
            "login": "marias",
            "visoes": []
        }

        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "marias", "password": "senha"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"].startswith("Olá Maria!")

    @patch("apps.users.services.login.AutenticacaoService.autentica", side_effect=Exception("Erro inesperado"))
    def test_erro_interno(self, mock_autentica):
        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "usuario", "password": "senha"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["detail"] == "Erro interno do sistema. Tente novamente mais tarde."