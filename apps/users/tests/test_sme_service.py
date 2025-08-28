import pytest
from unittest.mock import patch, MagicMock, ANY
from apps.users.services.sme_integracao_service import SmeIntegracaoService
from apps.helpers.exceptions import SmeIntegracaoException
import requests


@patch("requests.get")
class TestInformacaoUsuarioSGP:
    def test_sucesso_ao_buscar_usuario(self, mock_get):
        """Testa quando a API retorna os dados do usuário com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "professor@escola.com",
            "nome": "João Silva"
        }
        mock_get.return_value = mock_response

        resultado = SmeIntegracaoService.informacao_usuario_sgp("1234567")

        assert resultado["email"] == "professor@escola.com"
        mock_get.assert_called_once_with(
            ANY,
            headers=ANY,
            timeout=10
        )

    def test_usuario_nao_encontrado(self, mock_get):
        """Testa quando a API retorna que o usuário não existe"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(SmeIntegracaoException) as erro:
            SmeIntegracaoService.informacao_usuario_sgp("0000000")

        assert "Dados não encontrados" in str(erro.value)

    def test_erro_de_conexao(self, mock_get):
        """Testa quando há problemas para se conectar à API"""
        mock_get.side_effect = requests.RequestException("Erro ao conectar-se à API externa.")

        with pytest.raises(requests.RequestException) as erro:
            SmeIntegracaoService.informacao_usuario_sgp("1234567")

        assert "Erro ao conectar-se à API externa." in str(erro.value)

    @pytest.mark.parametrize("status_code", [500, 403, 418])
    def test_resposta_invalida(self, mock_get, status_code):
        """Testa quando a API retorna um status inesperado"""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.text = "Erro interno"
        mock_get.return_value = mock_response

        with pytest.raises(SmeIntegracaoException) as erro:
            SmeIntegracaoService.informacao_usuario_sgp("1234567")

        assert "Dados não encontrados" in str(erro.value)


@patch("apps.users.services.sme_integracao_service.requests.get")
class TestUsuarioCoreSSOOrNone:
    def test_usuario_encontrado(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "12345678901"}
        mock_get.return_value = mock_response

        result = SmeIntegracaoService.usuario_core_sso_or_none("12345678901")

        assert result == {"login": "12345678901"}

    def test_usuario_nao_encontrado(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        result = SmeIntegracaoService.usuario_core_sso_or_none("12345678901")

        assert result is None

    def test_request_exception(self, mock_get):
        mock_get.side_effect = requests.RequestException("Falha de rede")

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.usuario_core_sso_or_none("12345678901")

        assert "Erro ao procurar usuário" in str(exc.value)


@patch("apps.users.services.sme_integracao_service.requests.post")
class TestCriaUsuarioCoreSSO:
    def test_sucesso(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = SmeIntegracaoService.cria_usuario_core_sso(
            login="12345678901",
                nome="Usuário",
                email="usuario@example.com"
            )

        assert result is True

    def test_request_exception(self, mock_post):
        mock_post.side_effect = requests.RequestException("Erro HTTP")

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.cria_usuario_core_sso(
                login="12345678901",
                nome="Usuário",
                email="usuario@example.com"
            )

        assert "Erro ao criar o usuário" in str(exc.value)