import pytest
from django.contrib.auth import get_user_model
from apps.users.services.senha_service import SenhaService
from apps.helpers.exceptions import UserNotFoundError

from unittest.mock import patch, MagicMock
from apps.helpers.exceptions import SmeIntegracaoException
from apps.users.services.sme_integracao_service import SmeIntegracaoService
from rest_framework import status

User = get_user_model()

@pytest.mark.django_db
class TestSenhaService:
    def test_gerar_token_para_usuario(self):
        user = User.objects.create(username='1234567')
        uid, token = SenhaService.gerar_token_para_usuario(user)
       
        assert uid is not None
        assert token is not None
        assert isinstance(uid, str)
        assert isinstance(token, str)
 
    def test_gerar_token_para_reset_success(self):
        user = User.objects.create(
                    username='1234567',
                    email='test@example.com',
                    name='Test User'
                )        
        result = SenhaService.gerar_token_para_reset('1234567', 'test@example.com')
       
        assert 'token' in result
        assert 'uid' in result
        assert 'name' in result
        assert result['name'] == 'Test'


class TestSmeRedefinirSenhaService:
    def test_redefine_senha_success(self, monkeypatch):
        # Mock do requests.post
        mock_resp = MagicMock()
        mock_resp.status_code = status.HTTP_200_OK
        monkeypatch.setattr("apps.users.services.sme_integracao_service.requests.post", lambda *a, **k: mock_resp)

        # Não precisamos de URL real, pois requests foi mockado
        result = SmeIntegracaoService.redefine_senha("7210418", "NovaSenha@123")
        assert result == "OK"

    def test_redefine_senha_non_200_raises(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = status.HTTP_400_BAD_REQUEST
        mock_resp.content.decode.return_value = "Erro qualquer"
        monkeypatch.setattr("apps.users.services.sme_integracao_service.requests.post", lambda *a, **k: mock_resp)

        with pytest.raises(SmeIntegracaoException) as exc:
            SmeIntegracaoService.redefine_senha("7210418", "NovaSenha@123")
        assert "Erro ao redefinir senha" in str(exc.value)

    def test_redefine_senha_missing_args(self):
        with pytest.raises(SmeIntegracaoException):
            SmeIntegracaoService.redefine_senha("", "NovaSenha@123")

        with pytest.raises(SmeIntegracaoException):
            SmeIntegracaoService.redefine_senha("7210418", "")

