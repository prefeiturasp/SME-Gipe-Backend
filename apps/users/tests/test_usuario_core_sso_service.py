import pytest
from unittest.mock import patch
from requests import ReadTimeout
from rest_framework.test import APIClient
from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.helpers.exceptions import CargaUsuarioException, SmeIntegracaoException
from apps.users.services.usuario_core_sso_service import CriaUsuarioCoreSSOService

User = get_user_model()


@pytest.fixture
def dados_usuario_validos():
    return {
        "login": "11144477735",
        "nome": "Usuário Teste",
        "email": "teste@example.com",
    }

@pytest.fixture
def usuario_local(dados_usuario_validos):
    return User.objects.create_user(
        username=dados_usuario_validos["login"],
        email=dados_usuario_validos["email"],
        password="testpass123",
    )

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestCriaUsuarioCoreSSOService:

    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._validar_dados")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._criar_usuario")
    def test_cria_usuario_novo(self, mock_criar_usuario, mock_validar_dados, mock_usuario_existe, dados_usuario_validos, usuario_local):
        
        mock_usuario_existe.return_value = None
        mock_validar_dados.return_value = dados_usuario_validos

        CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        usuario_local.refresh_from_db()
        assert usuario_local.is_core_sso is True
        mock_criar_usuario.assert_called_once_with(dados_usuario_validos)

    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    def test_usuario_ja_existe(self, mock_usuario_existe, dados_usuario_validos, usuario_local):

        mock_usuario_existe.return_value = {"login": dados_usuario_validos["login"]}
        result = CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)
        usuario_local.refresh_from_db()

        assert result == {"login": dados_usuario_validos["login"]}
        assert usuario_local.is_core_sso is True

    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    def test_timeout_error(self, mock_usuario_existe, dados_usuario_validos):

        mock_usuario_existe.side_effect = ReadTimeout

        with pytest.raises(CargaUsuarioException) as exc:
            CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        assert "ReadTimeout" in str(exc.value)

    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    def test_erro_integracao(self, mock_usuario_existe, dados_usuario_validos):

        mock_usuario_existe.side_effect = SmeIntegracaoException("Falha externa")

        with pytest.raises(CargaUsuarioException) as exc:
            CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        assert "Falha externa" in str(exc.value)

    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    def test_erro_inesperado(self, mock_usuario_existe, dados_usuario_validos):

        mock_usuario_existe.side_effect = ValueError("Erro inesperado")

        with pytest.raises(CargaUsuarioException) as exc:
            CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        assert "Erro inesperado" in str(exc.value)

    @patch("apps.users.services.usuario_core_sso_service.User.objects.get")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    def test_usuario_local_nao_encontrado(self, mock_usuario_existe, mock_user_get, dados_usuario_validos):
        mock_usuario_existe.return_value = {"login": dados_usuario_validos["login"]}
        mock_user_get.side_effect = User.DoesNotExist

        with pytest.raises(CargaUsuarioException) as exc:
            CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        assert "não encontrado" in str(exc.value)

    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._validar_dados")
    def test_validacao_falha(self, mock_validar_dados, mock_usuario_existe, dados_usuario_validos):

        mock_usuario_existe.return_value = None
        mock_validar_dados.side_effect = serializers.ValidationError({"email": ["Inválido"]})

        with pytest.raises(CargaUsuarioException) as exc:
            CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        assert "Usuário inválido" in str(exc.value)
        assert "Email: Inválido" in str(exc.value)

    def test_usuario_existe_retorno(self, dados_usuario_validos):

        result = CriaUsuarioCoreSSOService._usuario_existe(dados_usuario_validos["login"])

        assert result is None

    def test_validar_dados_real(self, dados_usuario_validos):

        validated = CriaUsuarioCoreSSOService._validar_dados(dados_usuario_validos)

        assert validated["login"] == dados_usuario_validos["login"]
        assert validated["nome"] == dados_usuario_validos["nome"]
        assert validated["email"] == dados_usuario_validos["email"]

    def test_criar_usuario_chama_servico_core_sso(self, dados_usuario_validos):

        with patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.cria_usuario_core_sso") as mock_cria:
            CriaUsuarioCoreSSOService._criar_usuario(dados_usuario_validos)

            mock_cria.assert_called_once_with(
                login=dados_usuario_validos["login"],
                nome=dados_usuario_validos["nome"],
                email=dados_usuario_validos["email"]
            )