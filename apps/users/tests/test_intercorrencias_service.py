import requests
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.users.services.intercorrencias_service import IntercorrenciasService


class TestIntercorrenciasService:
    @patch.object(IntercorrenciasService, "BASE_URL", "http://intercorrencias")
    @patch.object(IntercorrenciasService, "INTERNAL_TOKEN", "internal-token")
    @patch("apps.users.services.intercorrencias_service.requests.post")
    def test_deletar_intercorrencias_usuario_inativo_sucesso(self, mock_post):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"intercorrencias_deletadas": 2}
        mock_post.return_value = response

        resultado = IntercorrenciasService.deletar_intercorrencias_usuario_inativo(
            username="usuario_teste"
        )

        assert resultado["success"] is True
        assert resultado["data"]["intercorrencias_deletadas"] == 2
        assert resultado["error"] is None
        assert resultado["error_type"] is None
        mock_post.assert_called_once_with(
            "http://intercorrencias/diretor/deletar-por-usuario-inativo/",
            json={"username": "usuario_teste"},
            headers={
                "Content-Type": "application/json",
                "X-Internal-Service-Token": "internal-token",
            },
            timeout=IntercorrenciasService.TIMEOUT,
        )

    @patch.object(IntercorrenciasService, "BASE_URL", "http://intercorrencias")
    @patch.object(IntercorrenciasService, "INTERNAL_TOKEN", "internal-token")
    @patch("apps.users.services.intercorrencias_service.requests.post", side_effect=requests.exceptions.Timeout)
    def test_deletar_intercorrencias_usuario_inativo_timeout(self, _mock_post):
        resultado = IntercorrenciasService.deletar_intercorrencias_usuario_inativo(
            username="usuario_teste"
        )

        assert resultado["success"] is False
        assert resultado["data"] is None
        assert resultado["error_type"] == "TIMEOUT"
        assert "Timeout" in resultado["error"]

    @patch.object(IntercorrenciasService, "BASE_URL", "http://intercorrencias")
    @patch.object(IntercorrenciasService, "INTERNAL_TOKEN", "internal-token")
    @patch(
        "apps.users.services.intercorrencias_service.requests.post",
        side_effect=requests.exceptions.ConnectionError("sem conexao"),
    )
    def test_deletar_intercorrencias_usuario_inativo_connection_error(self, _mock_post):
        resultado = IntercorrenciasService.deletar_intercorrencias_usuario_inativo(
            username="usuario_teste"
        )

        assert resultado["success"] is False
        assert resultado["data"] is None
        assert resultado["error_type"] == "CONNECTION_ERROR"
        assert "Falha ao conectar" in resultado["error"]

    @patch.object(IntercorrenciasService, "BASE_URL", "http://intercorrencias")
    @patch.object(IntercorrenciasService, "INTERNAL_TOKEN", "internal-token")
    @patch("apps.users.services.intercorrencias_service.requests.post")
    def test_deletar_intercorrencias_usuario_inativo_http_error(self, mock_post):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=MagicMock(status_code=500, json=MagicMock(return_value={"detail": "erro"}))
        )
        mock_post.return_value = response

        resultado = IntercorrenciasService.deletar_intercorrencias_usuario_inativo(
            username="usuario_teste"
        )

        assert resultado["success"] is False
        assert resultado["data"] is None
        assert resultado["error_type"] == "HTTP_500"
        assert "Erro HTTP 500" in resultado["error"]

    @patch.object(IntercorrenciasService, "BASE_URL", "http://intercorrencias")
    @patch.object(IntercorrenciasService, "INTERNAL_TOKEN", "internal-token")
    @patch("apps.users.services.intercorrencias_service.requests.post")
    def test_deletar_intercorrencias_usuario_inativo_http_error_sem_json(self, mock_post):
        response = MagicMock()
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.json.side_effect = ValueError("json invalido")
        http_error = requests.exceptions.HTTPError("falhou", response=error_response)
        response.raise_for_status.side_effect = http_error
        mock_post.return_value = response

        with patch(
            "apps.users.services.intercorrencias_service.Exception",
            SimpleNamespace(HTTPError=ValueError),
        ):
            resultado = IntercorrenciasService.deletar_intercorrencias_usuario_inativo(
                username="usuario_teste"
            )

        assert resultado["success"] is False
        assert resultado["data"] is None
        assert resultado["error_type"] == "HTTP_500"
        assert "falhou" in resultado["error"]

    @patch.object(IntercorrenciasService, "BASE_URL", "http://intercorrencias")
    @patch.object(IntercorrenciasService, "INTERNAL_TOKEN", "internal-token")
    @patch(
        "apps.users.services.intercorrencias_service.requests.post",
        side_effect=requests.exceptions.RequestException("erro request"),
    )
    def test_deletar_intercorrencias_usuario_inativo_request_exception(self, _mock_post):
        resultado = IntercorrenciasService.deletar_intercorrencias_usuario_inativo(
            username="usuario_teste"
        )

        assert resultado["success"] is False
        assert resultado["data"] is None
        assert resultado["error_type"] == "REQUEST_ERROR"

    @patch.object(IntercorrenciasService, "BASE_URL", "http://intercorrencias")
    @patch.object(IntercorrenciasService, "INTERNAL_TOKEN", "internal-token")
    @patch("apps.users.services.intercorrencias_service.requests.post", side_effect=Exception("boom"))
    def test_deletar_intercorrencias_usuario_inativo_erro_inesperado(self, _mock_post):
        resultado = IntercorrenciasService.deletar_intercorrencias_usuario_inativo(
            username="usuario_teste"
        )

        assert resultado["success"] is False
        assert resultado["data"] is None
        assert resultado["error_type"] == "UNEXPECTED_ERROR"
        assert "Erro inesperado" in resultado["error"]
