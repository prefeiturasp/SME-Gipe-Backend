import pytest
from unittest.mock import patch
from requests import ReadTimeout
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


@pytest.mark.django_db
class TestCriaUsuarioCoreSSOService:
    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.atribuir_perfil_coresso")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._validar_dados")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._criar_usuario")
    def test_cria_usuario_novo(
        self,
        mock_criar_usuario,
        mock_validar_dados,
        mock_usuario_existe,
        mock_atribuir,
        dados_usuario_validos,
        usuario_local,
    ):
        mock_usuario_existe.return_value = None
        mock_validar_dados.return_value = dados_usuario_validos

        CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        mock_criar_usuario.assert_called_once_with(dados_usuario_validos)

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.atribuir_perfil_coresso")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    def test_usuario_ja_existe(
        self, mock_usuario_existe, mock_atribuir, dados_usuario_validos, usuario_local
    ):
        mock_usuario_existe.return_value = {"login": dados_usuario_validos["login"]}

        result = CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_validos)

        assert result == {"login": dados_usuario_validos["login"]}
        mock_atribuir.assert_called_once_with(login=dados_usuario_validos["login"])

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

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.atribuir_perfil_coresso")
    @patch("apps.users.services.usuario_core_sso_service.User.objects.get")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._usuario_existe")
    def test_usuario_local_nao_encontrado(
        self, mock_usuario_existe, mock_user_get, mock_atribuir, dados_usuario_validos
    ):
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

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.usuario_core_sso_or_none")
    def test_usuario_existe_retorno(self, mock_usuario_core_sso_or_none, dados_usuario_validos):
        mock_usuario_core_sso_or_none.return_value = None
        result = CriaUsuarioCoreSSOService._usuario_existe(dados_usuario_validos["login"])
        mock_usuario_core_sso_or_none.assert_called_once_with(login=dados_usuario_validos["login"])
        assert result is None

    def test_validar_dados_real(self, dados_usuario_validos):
        validated = CriaUsuarioCoreSSOService._validar_dados(dados_usuario_validos)

        assert validated["login"] == dados_usuario_validos["login"]
        assert validated["nome"] == dados_usuario_validos["nome"]
        assert validated["email"] == dados_usuario_validos["email"]

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.atribuir_perfil_coresso")
    def test_criar_usuario_chama_servico_core_sso(self, mock_atribuir, dados_usuario_validos):
        User.objects.create_user(
            username=dados_usuario_validos["login"],
            email=dados_usuario_validos["email"],
            password="testpass123",
        )

        with patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.cria_usuario_core_sso") as mock_cria:
            CriaUsuarioCoreSSOService._criar_usuario(dados_usuario_validos)

            mock_cria.assert_called_once_with(
                login=dados_usuario_validos["login"],
                nome=dados_usuario_validos["nome"],
                email=dados_usuario_validos["email"],
            )
            mock_atribuir.assert_called_once_with(login=dados_usuario_validos["login"])

    def test_adiciona_perfil_guide_core_sso_chama_servico(self, dados_usuario_validos):
        with patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.atribuir_perfil_coresso") as mock_atribuir:
            CriaUsuarioCoreSSOService._adiciona_perfil_guide_core_sso(dados_usuario_validos["login"])
            mock_atribuir.assert_called_once_with(login=dados_usuario_validos["login"])

@pytest.mark.django_db
class TestRemoverPerfilUsuarioCoreSSO:

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.remover_perfil_coresso")
    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService._remover_flags_core_sso")
    def test_remover_perfil_usuario_sucesso(self, mock_remover_flags, mock_remover_perfil, usuario_local):
        """Testa remoção bem-sucedida do perfil do usuário"""
        login = usuario_local.username

        CriaUsuarioCoreSSOService.remover_perfil_usuario_core_sso(login)

        mock_remover_perfil.assert_called_once_with(login=login)
        mock_remover_flags.assert_called_once_with(login=login)

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.remover_perfil_coresso")
    def test_remover_perfil_timeout_error(self, mock_remover_perfil, usuario_local):
        """Testa tratamento de erro de timeout"""
        mock_remover_perfil.side_effect = ReadTimeout

        with pytest.raises(CargaUsuarioException):
            CriaUsuarioCoreSSOService.remover_perfil_usuario_core_sso(usuario_local.username)

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.remover_perfil_coresso")
    def test_remover_perfil_erro_integracao(self, mock_remover_perfil, usuario_local):
        """Testa tratamento de erro do serviço de integração"""
        mock_remover_perfil.side_effect = SmeIntegracaoException("Erro CoreSSO")

        with pytest.raises(CargaUsuarioException):
            CriaUsuarioCoreSSOService.remover_perfil_usuario_core_sso(usuario_local.username)

    @patch("apps.users.services.usuario_core_sso_service.SmeIntegracaoService.remover_perfil_coresso")
    def test_remover_perfil_erro_inesperado(self, mock_remover_perfil, usuario_local):
        """Testa tratamento de erro inesperado"""
        mock_remover_perfil.side_effect = Exception("Erro inesperado")

        with pytest.raises(CargaUsuarioException):
            CriaUsuarioCoreSSOService.remover_perfil_usuario_core_sso(usuario_local.username)


@pytest.mark.django_db
class TestRemoverFlagsCoreSSO:

    def test_remover_flags_sucesso(self, usuario_local):
        """Testa remoção bem-sucedida das flags"""
        usuario_local.is_core_sso = True
        usuario_local.is_validado = True
        usuario_local.save()

        CriaUsuarioCoreSSOService._remover_flags_core_sso(usuario_local.username)

        usuario_local.refresh_from_db()
        assert usuario_local.is_core_sso is False
        assert usuario_local.is_validado is False

    def test_remover_flags_usuario_nao_encontrado(self):
        """Testa usuário não encontrado"""
        with pytest.raises(CargaUsuarioException):
            CriaUsuarioCoreSSOService._remover_flags_core_sso("00000000000")