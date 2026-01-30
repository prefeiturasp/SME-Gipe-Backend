import pytest
from unittest.mock import patch, Mock

from apps.unidades.services.consulta_unidade_eol_service import ConsultaDadosEolService
from apps.helpers.exceptions import InternalError, SmeIntegracaoException


@pytest.mark.django_db
class TestConsultaDadosEolService:

    BASE_URL = "https://sme-integracao"

    @patch("apps.unidades.services.consulta_unidade_eol_service.env")
    @patch("apps.unidades.services.consulta_unidade_eol_service.requests.get")
    def test_consultar_dados_unidade_sucesso(
        self, mock_get, mock_env
    ):
        mock_env.return_value = self.BASE_URL
 
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "codigo": "222222",
            "nome": "UE Teste",
            "codigoDRE": "111111",
            "siglaTipoEscola": "CEI",
        }
        mock_get.return_value = mock_response

        result = ConsultaDadosEolService.consultar_dados_unidade("222222")

        mock_get.assert_called_once_with(
            f"{self.BASE_URL}/escolas/dados/222222",
            headers=ConsultaDadosEolService.DEFAULT_HEADERS,
            timeout=ConsultaDadosEolService.DEFAULT_TIMEOUT,
        )

        assert result["codigo"] == "222222"
        assert result["codigoDRE"] == "111111"

    @patch("apps.unidades.services.consulta_unidade_eol_service.env")
    @patch("apps.unidades.services.consulta_unidade_eol_service.requests.get")
    def test_consultar_dados_unidade_erro_http(
        self, mock_get, mock_env
    ):
        mock_env.return_value = self.BASE_URL

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        with pytest.raises(SmeIntegracaoException) as exc:
            ConsultaDadosEolService.consultar_dados_unidade("999999")

        assert "Erro ao consultar dados da escola" in str(exc.value)

    @patch("apps.unidades.services.consulta_unidade_eol_service.env")
    @patch("apps.unidades.services.consulta_unidade_eol_service.requests.get")
    def test_consultar_dados_unidade_payload_vazio(
        self, mock_get, mock_env
    ):
        mock_env.return_value = self.BASE_URL

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "codigo": None,
            "nome": None,
            "codigoDRE": None,
        }
        mock_get.return_value = mock_response

        with pytest.raises(SmeIntegracaoException) as exc:
            ConsultaDadosEolService.consultar_dados_unidade("000000")

        assert str(exc.value) == "Por favor, verifique se o código está correto e tente novamente."

    @patch("apps.unidades.services.consulta_unidade_eol_service.env")
    @patch("apps.unidades.services.consulta_unidade_eol_service.requests.get")
    def test_consultar_dados_unidade_erro_inesperado(
        self, mock_get, mock_env
    ):
        mock_env.return_value = self.BASE_URL

        mock_get.side_effect = Exception("Timeout")

        with pytest.raises(InternalError) as exc:
            ConsultaDadosEolService.consultar_dados_unidade("222222")

        assert "Erro interno" in str(exc.value)