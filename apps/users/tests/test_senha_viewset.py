import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from apps.users.api.views.senha_viewset import EsqueciMinhaSenhaViewSet
from rest_framework.exceptions import ValidationError
from apps.helpers.exceptions import SmeIntegracaoException

User = get_user_model()

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

