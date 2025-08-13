import pytest
import requests
from unittest.mock import patch, MagicMock
from apps.helpers.exceptions import UserNotFoundError
from apps.users.services.cargos_service import CargosService
from apps.helpers.enums import Cargo


class TestCargosService:

    @patch("apps.users.services.cargos_service.env")
    @patch("apps.users.services.cargos_service.requests.get")
    def test_get_cargos_sucesso(self, mock_get, mock_env):
        mock_env.return_value = "http://fake-api"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "cargos": [{"codigo": 1001, "descricao": "Cargo Teste"}]
        }
        mock_get.return_value = mock_response

        resultado = CargosService.get_cargos("123456", "João")

        assert "cargos" in resultado
        assert resultado["cargos"][0]["codigo"] == 1001

    @patch("apps.users.services.login_service.env")
    @patch("apps.users.services.login_service.requests.get")
    def test_get_cargos_usuario_nao_encontrado(self, mock_get, mock_env):
        mock_env.return_value = "http://fake-api"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(UserNotFoundError, match="Usuário não encontrado no sistema EOL"):
            CargosService.get_cargos("123456", "João")

    @patch("apps.users.services.cargos_service.env")
    @patch("apps.users.services.cargos_service.requests.get")
    def test_get_cargos_erro_http(self, mock_get, mock_env):
        mock_env.return_value = "http://fake-api"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Erro na consulta de cargos: 500"):
            CargosService.get_cargos("123456", "João")

    @patch("apps.users.services.cargos_service.env")
    @patch("apps.users.services.cargos_service.requests.get", side_effect=Exception("Erro inesperado"))
    def test_get_cargos_erro_inesperado(self, mock_get, mock_env):
        mock_env.return_value = "http://fake-api"

        with pytest.raises(Exception, match="Erro inesperado"):
            CargosService.get_cargos("123456", "João")

    @patch("apps.users.services.cargos_service.env")
    @patch("apps.users.services.cargos_service.requests.get", side_effect=requests.exceptions.RequestException("Timeout"))
    def test_get_cargos_request_exception(self, mock_get, mock_env):
        mock_env.return_value = "http://fake-api"

        with pytest.raises(Exception, match="Erro de comunicação com sistema de cargos: Timeout"):
            CargosService.get_cargos("123456", "João")

    def test_get_cargo_permitido_com_cargo_valido(self):
        dados = {
            "cargos": [
                {"codigo": Cargo.ASSISTENTE_DIRECAO.value, "descricao": "Assistente"},
                {"codigo": 9999, "descricao": "Outro Cargo"}
            ]
        }

        resultado = CargosService.get_cargo_permitido(dados)

        assert resultado["codigo"] == Cargo.ASSISTENTE_DIRECAO.value

    def test_get_cargo_permitido_sem_cargo_permitido(self):
        dados = {
            "cargos": [
                {"codigo": 9999, "descricao": "Cargo Irrelevante"}
            ]
        }

        resultado = CargosService.get_cargo_permitido(dados)

        assert resultado is None

    def test_get_cargo_permitido_lista_vazia(self):
        dados = {
            "cargos": []
        }

        resultado = CargosService.get_cargo_permitido(dados)

        assert resultado is None

    def test_get_cargo_permitido_com_cargos_sobrepostos(self):
        dados = {
            "cargosSobrePosto": [
                {"codigo": Cargo.DIRETOR_ESCOLA.value, "descricao": "Diretor"}
            ]
        }

        resultado = CargosService.get_cargo_permitido(dados)

        assert resultado["codigo"] == Cargo.DIRETOR_ESCOLA.value