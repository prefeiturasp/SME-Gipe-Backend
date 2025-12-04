import secrets
import pytest
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, APIClient

from apps.helpers.exceptions import (
    EmailNaoCadastrado,
    SmeIntegracaoException,
    UserNotFoundError,
)
from apps.users.api.views.senha_viewset import (
    AtualizarSenhaSerializer,
    AtualizarSenhaViewSet,
    EsqueciMinhaSenhaViewSet,
    RedefinirSenhaViewSet,
)


User = get_user_model()

@pytest.fixture
def factory():
    return APIRequestFactory()

@pytest.fixture
def view():
    return AtualizarSenhaViewSet()


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.user = MagicMock()
    request.user.username = "testuser"
    request.user.check_password.return_value = True
    request.user.id = 1
    return request

@pytest.fixture
def create_user(django_user_model):
    def _create(username="tester", email=None, **kwargs):
        pwd = secrets.token_urlsafe(16)
        user = django_user_model.objects.create_user(username=username, email=email)
        user.set_password(pwd)
        for k, v in kwargs.items():
            setattr(user, k, v)
        user.save()
        return user
    return _create


@pytest.mark.django_db
class TestEsqueciMinhaSenhaViewSet:
    
    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_fluxo_feliz(self, mock_enviar, mock_senha, mock_sme, create_user):
        mock_sme.return_value = {'email': 'teste@escola.com', 'nome': 'Fulano da Silva'}
        mock_senha.return_value = {'token': 'tokenxyz', 'uid': 'abc123', 'name': 'Fulano da Silva'}
        mock_enviar.return_value = None

        create_user(username='1234567', email='teste@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 200
        assert "Seu link de recuperação de senha foi enviado para tes**@escola.com" in response.data['detail']
        mock_senha.assert_called_once()
        mock_enviar.assert_called_once()

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_usuario_nao_encontrado_core_sso(self, mock_sme, create_user):
        mock_sme.side_effect = SmeIntegracaoException("Usuário não encontrado")
        create_user(username='1234567', email='teste@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'}) 
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.cargos_service.CargosService.get_cargos')
    @patch('apps.users.services.cargos_service.CargosService.get_cargo_permitido')
    def test_email_nao_cadastrado_diretor_assistente(self, mock_cargo_permitido, mock_cargos, mock_sme, create_user):
        mock_sme.return_value = {'email': None, 'nome': 'Diretor Teste'}
        mock_cargos.return_value = [{'codigo': 3360}]
        mock_cargo_permitido.return_value = [{'codigo': 3360, 'nome': 'DIRETOR'}]

        create_user(username='1234567', email='teste@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)
        assert response.status_code == 400
        assert "E-mail não encontrado" in response.data['detail']
        assert "Gabinete da Diretoria Regional de Educação (DRE)" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.cargos_service.CargosService.get_cargos')
    @patch('apps.users.services.cargos_service.CargosService.get_cargo_permitido')
    def test_fluxo_rf_sem_email_sem_cargo(self, mock_cargo_permitido, mock_cargos, mock_sme, create_user):
        mock_sme.return_value = {'email': None, 'nome': 'Professor Teste'}
        mock_cargos.return_value = [{'codigo': 9999}]
        mock_cargo_permitido.return_value = []

        create_user(username='1234567', email='teste@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)
        assert response.status_code == 401
        assert "acesso ao GIPE é restrito" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_fluxo_cpf_rede_indireta(self, mock_enviar, mock_senha, mock_sme, create_user):
        mock_sme.side_effect = SmeIntegracaoException("Não encontrado")
        mock_senha.return_value = {'token': 'tokenxyz', 'uid': 'abc123', 'name': 'Usuário Teste'}
        mock_enviar.return_value = None

        create_user(
            username='12345678901', 
            email='teste@indireta.com', 
            rede='INDIRETA', 
            is_validado=True
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        response = view.post(request)
        assert response.status_code == 200
        assert "Seu link de recuperação de senha foi enviado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_erro_inesperado(self, mock_sme, create_user):
        mock_sme.side_effect = Exception("Erro inesperado")
        create_user(username='1234567', email='teste@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)
        assert response.status_code == 500
        assert "Ocorreu um erro ao processar sua solicitação" in response.data['detail']

    def test_serializer_invalido(self):
        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={})
        with pytest.raises(ValidationError):
            view.post(request)

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_usuario_nao_encontrado_local(self, mock_sme, create_user):
        mock_sme.return_value = {'email': 'teste@escola.com', 'nome': 'Fulano da Silva'}
        create_user(
            username='12345678901', 
            email='teste@indireta.com', 
            rede='INDIRETA', 
            is_validado=True
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '9999999'})
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.cargos_service.CargosService.get_cargos')
    @patch('apps.users.services.cargos_service.CargosService.get_cargo_permitido')
    def test_rf_sem_email_com_cargo_gipe(self, mock_cargo_permitido, mock_cargos, mock_sme, create_user):
        mock_sme.return_value = {'email': None, 'nome': 'Usuário GIPE'}
        mock_cargos.return_value = []
        mock_cargo_permitido.return_value = []

        from apps.users.models import Cargo
        cargo_gipe = Cargo.objects.create(codigo=1, nome="Cargo GIPE")
        create_user(username='1234567', email='', cargo=cargo_gipe)

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)
        assert response.status_code == 400
        assert "E-mail não encontrado" in response.data['detail']
        assert "GIPE" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_diretor_sem_email(self, mock_sme, create_user):
        mock_sme.return_value = {'email': None, 'nome': 'Diretor Teste'}
        from apps.users.models import Cargo
        cargo_diretor = Cargo.objects.create(codigo=3360, nome="DIRETOR")
        create_user(username='12345678901', email='', cargo=cargo_diretor)

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        response = view.post(request)
        assert response.status_code == 400
        assert "E-mail não encontrado" in response.data['detail']
        assert "Gabinete da Diretoria Regional de Educação (DRE)" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_nao_encontrado_nem_local_nem_core(self, mock_sme, create_user):
        mock_sme.side_effect = SmeIntegracaoException("Não encontrado")
        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_encontrado_local_sem_email(self, mock_sme, create_user):
        mock_sme.side_effect = SmeIntegracaoException("Não encontrado")
        create_user(username='12345678901', email='', rede='DIRETA', is_validado=False)

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        response = view.post(request)
        assert response.status_code == 400
        assert "E-mail não encontrado" in response.data['detail']
        assert "Gabinete da Diretoria Regional de Educação (DRE)" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_fluxo_nao_tratado(self, mock_sme, create_user):
        mock_sme.return_value = {}
        create_user(username='12345678901', email='teste@escola.com', rede='Direta')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_fluxo_coresso_nao_diretor(self, mock_sme, create_user):
        mock_sme.return_value = {'email': None, 'nome': 'Usuário Teste'}
        create_user(username='12345678901', email='teste@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        response = view.post(request)
        assert response.status_code == 401
        assert "Olá Usuário! Desculpe, mas o acesso ao GIPE é restrito a perfis específicos." in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_anonimizar_email_curto(self, mock_enviar, mock_senha, mock_sme, create_user):
        mock_sme.return_value = {'email': 'ab@escola.com', 'nome': 'Fulano da Silva'}
        mock_senha.return_value = {'token': 'tokenxyz', 'uid': 'abc123', 'name': 'Fulano da Silva'}
        mock_enviar.return_value = None

        create_user(username='1234567', email='ab@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)
        assert response.status_code == 200
        assert "a*@escola.com" in response.data['detail'] or "ab@escola.com" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_anonimizar_email_1_caractere(self, mock_enviar, mock_senha, mock_sme, create_user):
        mock_sme.return_value = {'email': 'a@escola.com', 'nome': 'Fulano da Silva'}
        mock_senha.return_value = {'token': 'tokenxyz', 'uid': 'abc123', 'name': 'Fulano da Silva'}
        mock_enviar.return_value = None

        create_user(username='1234567', email='a@escola.com')

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)
        assert response.status_code == 200
        assert "a@escola.com" in response.data['detail']


class TestRedefinirSenhaViewSet:

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
    def test_post_success(self, db, factory, create_user, monkeypatch):
        user = create_user(username='usuario')

        view = RedefinirSenhaViewSet.as_view()
        old_hash = user.password

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {"uid": uid, "token": token, "password": "NovaSenha@123", "password2": "NovaSenha@123"}

        def _mock_success(username, senha):
            return "OK"

        monkeypatch.setattr(
            "apps.users.services.sme_integracao_service.SmeIntegracaoService.redefine_senha",
            _mock_success
        )

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"

        fresh = User.objects.get(pk=user.pk)
        assert fresh.password != old_hash

    def test_post_integration_error(self, db, factory, create_user, monkeypatch):
        user = create_user(username='usuario')

        view = RedefinirSenhaViewSet.as_view()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {"uid": uid, "token": token, "password": "SenhaPadr@o1", "password2": "SenhaPadr@o1"}

        def _mock_fail(username, senha):
            raise SmeIntegracaoException("Regra do SME: não permitido")

        monkeypatch.setattr(
            "apps.users.services.sme_integracao_service.SmeIntegracaoService.redefine_senha",
            _mock_fail
        )

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"
        assert "não permitido" in response.data["detail"]

        user.refresh_from_db()
        assert not user.check_password("SenhaPadr@o1")

    def test_post_invalid_serializer(self, db, factory, create_user):
        user = create_user(username='usuario')

        view = RedefinirSenhaViewSet.as_view()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {"uid": uid, "token": token, "password": "NovaSenha@123", "password2": "OutraSenha@123"}

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"

    def test_post_erro_inesperado(self, db, factory, create_user, monkeypatch):
        user = create_user(username='usuario')

        view = RedefinirSenhaViewSet.as_view()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {"uid": uid, "token": token, "password": "SenhaPadr@o1", "password2": "SenhaPadr@o1"}

        class SmeValidationError(Exception):
            pass

        def _mock_fail(username, senha):
            raise SmeValidationError("Regra do SME: não permitido")

        monkeypatch.setattr(
            "apps.users.services.sme_integracao_service.SmeIntegracaoService.redefine_senha",
            _mock_fail
        )

        request = factory.post("/users/password/reset/", data, format="json")
        response = view(request)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestAtualizarSenhaViewSet:

    def test_sucesso(self, view, mock_request):
        mock_request.data = {
            "username": "testuser",
            "senha_atual": "senhaantiga",
            "nova_senha": "novasenha123",
            "confirmacao_nova_senha": "novasenha123"
        }

        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.validated_data = {"nova_senha": "novasenha123"}
        
        with patch('apps.users.api.serializers.senha_serializer.AtualizarSenhaSerializer') as mock_serializer_class:
            mock_serializer_class.return_value = mock_serializer
            
            with patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.redefine_senha'):
                with patch.object(mock_request.user, 'set_password'):
                    with patch.object(mock_request.user, 'save'):
                        response = view.post(mock_request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Senha alterada com sucesso."

    def test_validation_error_confirmacao_senha_nao_corresponde(self, view, mock_request):
        mock_request.data = {
            "username": "testuser",
            "senha_atual": "senhaantiga",
            "nova_senha": "novasenha123",
            "confirmacao_nova_senha": "diferente"
        }

        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        mock_serializer.errors = {"confirmacao_nova_senha": ["As senhas não coincidem."]}
        
        with patch('apps.users.api.serializers.senha_serializer.AtualizarSenhaSerializer') as mock_serializer_class:
            mock_serializer_class.return_value = mock_serializer
            
            response = view.post(mock_request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validation_error_senha_atual_incorreta_pela_view(self, view, mock_request):
        mock_request.data = {
            "username": "testuser",
            "senha_atual": "senha_errada",
            "nova_senha": "novasenha123",
            "confirmacao_nova_senha": "novasenha123"
        }

        mock_request.user.check_password.return_value = False

        response = view.post(mock_request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Senha atual incorreta."
        assert response.data["field"] == "senha_atual"

    def test_serializer_raise_exception_true_line(self, mock_request):
        data = {
            "username": "",
            "senha_atual": "",
            "nova_senha": "",
            "confirmacao_nova_senha": ""
        }

        serializer = AtualizarSenhaSerializer(
            data=data,
            context={"request": mock_request}
        )

        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.is_valid(raise_exception=True)

        detail = exc_info.value.detail
        assert "detail" in detail
        assert "field" in detail

    def test_erro_sme(self, view, mock_request):
        mock_request.data = {
            "username": "testuser",
            "senha_atual": "senhaantiga",
            "nova_senha": "novasenha123",
            "confirmacao_nova_senha": "novasenha123"
        }

        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.validated_data = {"nova_senha": "novasenha123"}
        
        with patch('apps.users.api.serializers.senha_serializer.AtualizarSenhaSerializer') as mock_serializer_class:
            mock_serializer_class.return_value = mock_serializer
            
            with patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.redefine_senha', 
                      side_effect=SmeIntegracaoException("Erro SME")):
                response = view.post(mock_request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Erro SME" in response.data["detail"]

    def test_erro_inesperado(self, view, mock_request):
        mock_request.data = {
            "username": "testuser",
            "senha_atual": "senhaantiga",
            "nova_senha": "novasenha123",
            "confirmacao_nova_senha": "novasenha123"
        }

        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.validated_data = {"nova_senha": "novasenha123"}
        
        with patch('apps.users.api.serializers.senha_serializer.AtualizarSenhaSerializer') as mock_serializer_class:
            mock_serializer_class.return_value = mock_serializer
            
            with patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.redefine_senha', 
                      side_effect=Exception("Erro inesperado")):
                with patch('apps.users.api.views.senha_viewset.logger.exception'):
                    response = view.post(mock_request)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["detail"] == "Erro interno do servidor."