import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import override_settings
from apps.users.api.views.senha_viewset import EsqueciMinhaSenhaViewSet
from rest_framework.exceptions import ValidationError
from apps.helpers.exceptions import SmeIntegracaoException
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.test import APIRequestFactory
from rest_framework import status
from apps.users.api.views.senha_viewset import RedefinirSenhaViewSet

User = get_user_model()

@pytest.fixture
def factory():
    return APIRequestFactory()

@pytest.mark.django_db
class TestEsqueciMinhaSenhaViewSet:
    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_fluxo_feliz(self, mock_enviar, mock_senha, mock_sme):
        """Testa o caso de sucesso (tudo funciona)"""
        mock_sme.return_value = {'email': 'teste@escola.com'}
        mock_senha.return_value = {
            'token': 'tokenxyz',
            'uid': 'abc123',
            'name': 'Fulano'
        }
        mock_enviar.return_value = None

        User.objects.create(username='1234567', name='Fulano da Silva')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 200
        assert response.data == 'Email enviado com sucesso'

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_email_nao_cadastrado(self, mock_sme):
        """Testa quando o usuário não tem email cadastrado"""
        mock_sme.return_value = {'email': None}

        User.objects.create(username='1234567')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 404
        assert 'não tem e-mail cadastrado' in response.data['message']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_erro_api_externa(self, mock_sme):
        """Testa quando a API da SME falha"""
        mock_sme.side_effect = Exception("API fora do ar")

        User.objects.create(username='1234567')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 500
        assert 'erro ao processar' in response.data['message'].lower()

    @patch("apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp")
    def test_sme_integracao_exception(self, mock_sme):
        """Testa quando a SME levanta SmeIntegracaoException"""
        mock_sme.side_effect = SmeIntegracaoException("Falha na integração")

        User.objects.create(username="1234567")

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={"username": "1234567"})
        response = view.post(request)

        assert response.status_code == 204
        assert response.data["status"] == "error"
        assert "Falha na integração" in response.data["message"]

    @pytest.mark.django_db
    def test_usuario_nao_encontrado_serializer(self):
        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={"username": "0000000"})

        with pytest.raises(ValidationError) as exc_info:
            view.post(request)

        assert "Usuário 0000000 não encontrado." in str(exc_info.value)


class TestRedefinirSenhaViewSet:

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
    def test_post_success(self, db, factory, user, monkeypatch):
        """
        Fluxo feliz:
        - Serializer valida uid/token/senhas
        - Service externo retorna sucesso
        - Senha é atualizada localmente
        - Retorna 200
        """
        view = RedefinirSenhaViewSet.as_view()

        # Guarda o hash antigo para comparar depois
        old_hash = user.password

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {
            "uid": uid,
            "token": token,
            "password": "NovaSenha@123",
            "password2": "NovaSenha@123",
        }

        # Mocka o serviço externo para sucesso
        def _mock_success(username, senha):
            return "OK"

        monkeypatch.setattr(
            "apps.users.api.views.senha_viewset.SmeIntegracaoService.redefine_senha",
            _mock_success
        )

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"

        # Recarrega a partir do BD numa NOVA instância

        fresh = User.objects.get(pk=user.pk)

        # 1) Hash mudou
        assert fresh.password != old_hash, "O hash da senha não foi alterado no banco."


    def test_post_integration_error(self, db, factory, user, monkeypatch):
        """
        Quando o serviço externo falha (ex.: regra de senha padrão),
        a view deve retornar 400 e NÃO atualizar a senha local.
        """
        view = RedefinirSenhaViewSet.as_view()

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {
            "uid": uid,
            "token": token,
            "password": "SenhaPadr@o1",
            "password2": "SenhaPadr@o1",
        }

        def _mock_fail(username, senha):
            raise SmeIntegracaoException("Regra do SME: não permitido")

        monkeypatch.setattr(
            "apps.users.api.views.senha_viewset.SmeIntegracaoService.redefine_senha",
            _mock_fail
        )

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"
        assert "não permitido" in response.data["message"]

        # Senha local não deve ter sido alterada
        user.refresh_from_db()
        assert not user.check_password("SenhaPadr@o1")

    def test_post_invalid_serializer(self, db, factory, user):
        """
        Dados inválidos (ex.: senhas diferentes) devem retornar 400
        com o payload de errors do serializer.
        """
        view = RedefinirSenhaViewSet.as_view()

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {
            "uid": uid,
            "token": token,
            "password": "NovaSenha@123",
            "password2": "OutraSenha@123",
        }

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"
        assert "errors" in response.data


    def test_post_erro_inesperado(self, db, factory, user, monkeypatch):
        """
        Quando o serviço externo falha (ex.: regra de senha padrão),
        a view deve retornar 400 e NÃO atualizar a senha local.
        """
        view = RedefinirSenhaViewSet.as_view()

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {
            "uid": uid,
            "token": token,
            "password": "SenhaPadr@o1",
            "password2": "SenhaPadr@o1",
        }

        class SmeValidationError(Exception):
            """Specific exception for SME service validation errors"""
            pass

        def _mock_fail(username, senha):
            raise SmeValidationError("Regra do SME: não permitido")

        monkeypatch.setattr(
            "apps.users.api.views.senha_viewset.SmeIntegracaoService.redefine_senha",
            _mock_fail
        )

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["status"] == "error"
        assert "Erro interno do servidor. Tente novamente mais tarde." in response.data["message"]

        # Senha local não deve ter sido alterada
        user.refresh_from_db()
        assert not user.check_password("SenhaPadr@o1")