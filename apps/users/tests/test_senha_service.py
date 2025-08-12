import pytest
from django.contrib.auth import get_user_model
from apps.users.services.senha_service import SenhaService
from apps.helpers.exceptions import UserNotFoundError

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
