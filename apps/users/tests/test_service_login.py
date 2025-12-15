import pytest
import requests
from unittest.mock import patch, MagicMock
from apps.helpers.exceptions import AuthenticationError, SmeIntegracaoException, InternalError
from apps.users.services.login_service import AutenticacaoService

class TestAutenticacaoService:

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post")
    def test_autenticacao_sucesso(self, mock_post, mock_env):
        mock_env.return_value = "https://fake-api"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "usuario123", "nome": "Usuário Teste"}
        mock_post.return_value = mock_response

        resultado = AutenticacaoService.autentica("usuario123", "senha")

        assert resultado["login"] == "usuario123"
        assert resultado["nome"] == "Usuário Teste"

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post")
    def test_autenticacao_falha_status_code(self, mock_post, mock_env):
        mock_env.return_value = "https://fake-api"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with pytest.raises(AuthenticationError, match="Credenciais inválidas"):
            AutenticacaoService.autentica("usuario123", "senha_incorreta")

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post", side_effect=Exception("Erro inesperado"))
    def test_erro_inesperado(self, mock_post, mock_env):
        mock_env.return_value = "https://fake-api"

        with pytest.raises(InternalError, match="Erro interno: Erro inesperado"):
            AutenticacaoService.autentica("usuario123", "senha")

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post", side_effect=Exception("Falha de rede"))
    def test_erro_requisicao(self, mock_post, mock_env):
        mock_env.return_value = "https://fake-api"

        with pytest.raises(InternalError) as exc:
            AutenticacaoService.autentica("usuario123", "senha")

        assert "Erro interno: Falha de rede" in str(exc.value)

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post", side_effect=requests.exceptions.RequestException("Timeout"))
    def test_erro_requests_exception(self, mock_post, mock_env):
        mock_env.return_value = "https://fake-api"

        with pytest.raises(SmeIntegracaoException, match="Erro de comunicação: Timeout"):
            AutenticacaoService.autentica("usuario123", "senha")

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post")
    def test_autenticacao_service_erro_http_500(self, mock_post, mock_env):
        """Deve levantar SmeIntegracaoException quando a API externa retornar 500"""
        mock_env.return_value = "https://fake-api"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with pytest.raises(SmeIntegracaoException, match="Erro ao autenticar no CoreSSO: 500"):
            AutenticacaoService.autentica("usuario123", "senha_invalida")