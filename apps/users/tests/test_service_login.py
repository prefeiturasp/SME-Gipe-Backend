import pytest
import requests
from unittest.mock import patch, MagicMock
from apps.helpers.exceptions import AuthenticationError, UserNotFoundError, InternalError
from apps.users.services.login_service import AutenticacaoService
from apps.users.models import User

class TestAutenticacaoService:

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post")
    def test_autenticacao_sucesso(self, mock_post, mock_env):
        mock_env.return_value = "http://fake-api"
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
        mock_env.return_value = "http://fake-api"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with pytest.raises(AuthenticationError, match="Credenciais inválidas"):
            AutenticacaoService.autentica("usuario123", "senha_incorreta")

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post", side_effect=Exception("Erro inesperado"))
    def test_erro_inesperado(self, mock_post, mock_env):
        mock_env.return_value = "http://fake-api"

        with pytest.raises(AuthenticationError, match="Erro interno: Erro inesperado"):
            AutenticacaoService.autentica("usuario123", "senha")

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post", side_effect=Exception("Falha de rede"))
    def test_erro_requisicao(self, mock_post, mock_env):
        mock_env.return_value = "http://fake-api"

        with pytest.raises(AuthenticationError) as exc:
            AutenticacaoService.autentica("usuario123", "senha")

        assert "Erro interno: Falha de rede" in str(exc.value)

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.post", side_effect=requests.exceptions.RequestException("Timeout"))
    def test_erro_requests_exception(self, mock_post, mock_env):
        mock_env.return_value = "http://fake-api"

        with pytest.raises(AuthenticationError, match="Erro de comunicação: Timeout"):
            AutenticacaoService.autentica("usuario123", "senha")


@pytest.fixture
def fake_user():
    user = MagicMock()
    user.check_password.return_value = True
    user.rede = "INDIRETA"
    user.name = "Usuario"
    user.email = "usuario@email.com"
    user.cpf = "12345678900"
    user.username = "usuario_login"
    user.cargo.codigo = "123"
    user.cargo.nome = "Analista"
    user.unidades.all.return_value.values.return_value = [
        {"codigo_eol": "456", "nome": "Unidade X"}
    ]
    user.unidades.exists.return_value = True
    return user


class TestAuthenticateUserByCPF:

    @patch("apps.users.services.login_service.User")
    @patch("apps.users.services.login_service.RefreshToken")
    def test_authenticate_success(self, mock_refresh_token, mock_user_model, fake_user):
        mock_user_model.objects.get.return_value = fake_user
        mock_refresh_token.for_user.return_value.access_token = "fake_token"

        result = AutenticacaoService._authenticate_user_by_cpf("12345678900", "senha123")

        assert result["cpf"] == "12345678900"
        assert result["name"] == "Usuario"
        assert result["perfil_acesso"]["codigo"] == "123"
        assert result["token"] == "fake_token"
        fake_user.save.assert_called_once()

    @patch("apps.users.services.login_service.User.objects.get")
    def test_authenticate_user_not_found(self, mock_get):
        mock_get.side_effect = User.DoesNotExist

        with pytest.raises(AuthenticationError):
            AutenticacaoService._authenticate_user_by_cpf("00000000000", "senha")

    @patch("apps.users.services.login_service.User.objects.get")
    def test_authenticate_invalid_password(self, mock_get, fake_user):
        fake_user.check_password.return_value = False
        mock_get.return_value = fake_user

        with pytest.raises(AuthenticationError):
            AutenticacaoService._authenticate_user_by_cpf("12345678900", "senha_errada")

    @patch("apps.users.services.login_service.User.objects.get")
    def test_authenticate_user_wrong_rede(self, mock_get, fake_user):
        fake_user.rede = "DIRETA"
        mock_get.return_value = fake_user

        with pytest.raises(UserNotFoundError):
            AutenticacaoService._authenticate_user_by_cpf("12345678900", "senha")

    @patch("apps.users.services.login_service.User.objects.get")
    def test_authenticate_internal_error(self, mock_get):
        mock_get.side_effect = Exception("Erro desconhecido")

        with pytest.raises(InternalError):
            AutenticacaoService._authenticate_user_by_cpf("12345678900", "senha")