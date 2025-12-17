import pytest
from rest_framework import status
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

@patch("apps.users.services.sme_integracao_service.requests.post")
class TestAlteraEmail:

    def test_sucesso(self, mock_post):
        """Deve retornar OK quando a API responde 200"""
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_200_OK
        mock_post.return_value = mock_response

        result = SmeIntegracaoService.altera_email("1234567", "teste@sme.prefeitura.sp.gov.br")

        assert result == "OK"
        mock_post.assert_called_once()

    def test_parametros_invalidos(self, mock_post):
        """Deve lançar exceção se registro_funcional ou email forem vazios"""
        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.altera_email("", "teste@sme.prefeitura.sp.gov.br")
        assert "Registro funcional e email são obrigatórios" in str(exc.value)

        with pytest.raises(SmeIntegracaoException):
            SmeIntegracaoService.altera_email("1234567", "")

        mock_post.assert_not_called()

    def test_erro_api(self, mock_post):
        """Deve lançar exceção quando API responde status != 200"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"mensagem":"Erro API"}'
        mock_post.return_value = mock_response

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.altera_email("1234567", "teste@sme.prefeitura.sp.gov.br")

        assert "Erro API" in str(exc.value)
        mock_post.assert_called_once()

    def test_excecao_generica(self, mock_post):
        """Deve encapsular erros inesperados em SmeIntegracaoException"""
        mock_post.side_effect = requests.RequestException("Falha de rede")

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.altera_email("1234567", "teste@sme.prefeitura.sp.gov.br")

        assert "Falha de rede" in str(exc.value)
        mock_post.assert_called_once()


@patch("apps.users.services.sme_integracao_service.requests.get")
class TestAtribuirPerfilCoresso:

    def test_sucesso(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_200_OK
        mock_get.return_value = mock_response

        result = SmeIntegracaoService.atribuir_perfil_coresso("1234567")

        assert result is None
        mock_get.assert_called_once()

    def test_erro_api(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Erro ao atribuir perfil"
        mock_get.return_value = mock_response

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.atribuir_perfil_coresso("1234567")

        assert "Falha ao fazer atribuição de perfil" in str(exc.value)
        mock_get.assert_called_once()

    def test_excecao_generica(self, mock_get):
        mock_get.side_effect = requests.RequestException("Falha de rede")

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.atribuir_perfil_coresso("1234567")

        assert "Falha de rede" in str(exc.value)
        mock_get.assert_called_once()


@patch("apps.users.services.sme_integracao_service.requests.delete")
class TestRemoverPerfilUsuarioCoreSSO:

    def test_sucesso(self, mock_delete):
        """Deve retornar None quando a API responde 200"""
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_200_OK
        mock_delete.return_value = mock_response

        result = SmeIntegracaoService.remover_perfil_coresso(
            login="1234567"
        )

        assert result is None
        mock_delete.assert_called_once()
        _, kwargs = mock_delete.call_args
        assert "data" in kwargs
        assert kwargs["data"]["codigoRF"] == "1234567"
        assert "perfilGuid" in kwargs["data"]

    def test_erro_api(self, mock_post):
        """Deve lançar exceção se a API retornar status != 200"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Erro ao remover perfil"
        mock_post.return_value = mock_response

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.remover_perfil_coresso(
                login="1234567"            )

        assert "Falha ao fazer remoção de perfil." in str(exc.value)
        mock_post.assert_called_once()

    def test_excecao_generica(self, mock_delete):
        """Deve encapsular exceções inesperadas em SmeIntegracaoException"""
        mock_delete.side_effect = requests.RequestException("Falha de rede")

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.remover_perfil_coresso(
                login="1234567"
            )

        assert "Falha de rede" in str(exc.value)
        mock_delete.assert_called_once()