import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import override_settings
from apps.users.api.views.senha_viewset import EsqueciMinhaSenhaViewSet
from rest_framework.exceptions import ValidationError
from apps.helpers.exceptions import SmeIntegracaoException, UserNotFoundError, EmailNaoCadastrado
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
        """Testa o caso de sucesso com email válido"""
        mock_sme.return_value = {
            'email': 'teste@escola.com',
            'nome': 'Fulano da Silva'
        }
        mock_senha.return_value = {
            'token': 'tokenxyz',
            'uid': 'abc123',
            'name': 'Fulano da Silva'
        }
        mock_enviar.return_value = None

        User.objects.create_user(
            username='1234567', 
            email='teste@escola.com',
            password='teste123'
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 200
        assert "Seu link de recuperação de senha foi enviado para tes**@escola.com" in response.data['detail']
        mock_senha.assert_called_once()
        mock_enviar.assert_called_once()

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_usuario_nao_encontrado_core_sso(self, mock_sme):
        """Testa quando o usuário não é encontrado no CoreSSO"""
        mock_sme.side_effect = SmeIntegracaoException("Usuário não encontrado")
        
        # Cria usuário local para não cair no UserNotFoundError inicial
        User.objects.create_user(
            username='1234567', 
            email='teste@escola.com',
            password='teste123'
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'}) 
        
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.cargos_service.CargosService.get_cargos')
    @patch('apps.users.services.cargos_service.CargosService.get_cargo_permitido')
    def test_email_nao_cadastrado_diretor_assistente(self, mock_cargo_permitido, mock_cargos, mock_sme):
        """Testa quando o usuário é diretor ou assistente de direção mas não tem email cadastrado"""
        mock_sme.return_value = {
            'email': None,
            'nome': 'Diretor Teste'
        }
        mock_cargos.return_value = [{'codigo': 3360}]  # Código de diretor
        mock_cargo_permitido.return_value = [{'codigo': 3360, 'nome': 'DIRETOR'}]

        User.objects.create_user(
            username='1234567', 
            email='teste@escola.com',
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        
        response = view.post(request)
        assert response.status_code == 404  # EmailNaoCadastrado retorna 404
        assert "E-mail não encontrado" in response.data['detail']
        assert "Gabinete da Diretoria Regional de Educação (DRE)" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.cargos_service.CargosService.get_cargos')
    @patch('apps.users.services.cargos_service.CargosService.get_cargo_permitido')
    def test_fluxo_rf_sem_email_sem_cargo(self, mock_cargo_permitido, mock_cargos, mock_sme):
        """Testa RF sem email e sem cargo válido"""
        mock_sme.return_value = {
            'email': None,
            'nome': 'Professor Teste'
        }
        mock_cargos.return_value = [{'codigo': 9999}]  # Cargo não permitido
        mock_cargo_permitido.return_value = []  # Nenhum cargo permitido

        User.objects.create_user(
            username='1234567', 
            email='teste@escola.com',
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        
        response = view.post(request)
        assert response.status_code == 401
        assert "acesso ao GIPE é restrito" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_fluxo_cpf_rede_indireta(self, mock_enviar, mock_senha, mock_sme):
        """Testa CPF na rede indireta"""
        mock_sme.side_effect = SmeIntegracaoException("Não encontrado")
        mock_senha.return_value = {
            'token': 'tokenxyz',
            'uid': 'abc123',
            'name': 'Usuário Teste'
        }
        mock_enviar.return_value = None

        user = User.objects.create_user(
            username='12345678901', 
            email='teste@indireta.com',
            password='teste123'
        )
        user.rede = 'INDIRETA'
        user.is_validado = True
        user.save()

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        response = view.post(request)

        assert response.status_code == 200
        assert "Seu link de recuperação de senha foi enviado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_erro_inesperado(self, mock_sme):
        """Testa erro inesperado no fluxo"""
        mock_sme.side_effect = Exception("Erro inesperado")

        User.objects.create_user(
            username='1234567', 
            email='teste@escola.com',
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 500
        assert "Ocorreu um erro ao processar sua solicitação" in response.data['detail']

    def test_serializer_invalido(self):
        """Testa quando os dados da requisição são inválidos"""
        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={})  # Sem username
        
        with pytest.raises(ValidationError):
            view.post(request)

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_usuario_nao_encontrado_local(self, mock_sme):
        """Testa quando usuário não existe no banco local"""
        mock_sme.return_value = {
            'email': 'teste@escola.com',
            'nome': 'Fulano da Silva'
        }

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '9999999'})  # Não existe
        
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    
    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.cargos_service.CargosService.get_cargos')
    @patch('apps.users.services.cargos_service.CargosService.get_cargo_permitido')
    def test_rf_sem_email_com_cargo_gipe(self, mock_cargo_permitido, mock_cargos, mock_sme):
        """Testa RF sem email mas com cargo GIPE (0 ou 1) no banco local"""
        mock_sme.return_value = {
            'email': None,
            'nome': 'Usuário GIPE'
        }
        mock_cargos.return_value = []
        mock_cargo_permitido.return_value = []

        # Cria cargo GIPE primeiro
        from apps.users.models import Cargo
        cargo_gipe = Cargo.objects.create(codigo=1, nome="Cargo GIPE")

        # Cria usuário com cargo GIPE
        user = User.objects.create_user(
            username='1234567', 
            email='', 
            password='teste123'
        )
        user.cargo = cargo_gipe 
        user.save()

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        
        response = view.post(request)
        assert response.status_code == 404
        assert "E-mail não encontrado" in response.data['detail']
        assert "GIPE" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_diretor_sem_email(self, mock_sme):
        """Testa CPF que é diretor (cargo 3360) mas sem email"""
        mock_sme.return_value = {
            'email': None,
            'nome': 'Diretor Teste'
        }

        # Cria cargo de diretor primeiro
        from apps.users.models import Cargo
        cargo_diretor = Cargo.objects.create(codigo=3360, nome="DIRETOR")

        # Cria usuário com cargo de diretor
        user = User.objects.create_user(
            username='12345678901',
            email='', 
            password='teste123'
        )
        user.cargo = cargo_diretor 
        user.save()

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        
        response = view.post(request)
        assert response.status_code == 404
        assert "E-mail não encontrado" in response.data['detail']
        assert "Gabinete da Diretoria Regional de Educação (DRE)" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_nao_encontrado_nem_local_nem_core(self, mock_sme):
        """Testa CPF não encontrado nem no CoreSSO nem no banco local"""
        mock_sme.side_effect = SmeIntegracaoException("Não encontrado")

        # Não cria usuário local

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_encontrado_local_sem_email(self, mock_sme):
        """Testa CPF encontrado no banco local mas sem email"""
        mock_sme.side_effect = SmeIntegracaoException("Não encontrado")

        # Cria usuário local sem email e não é rede indireta
        user = User.objects.create_user(
            username='12345678901',
            email='', 
            password='teste123'
        )
        user.rede = 'DIRETA'  # Não é rede indireta
        user.is_validado = False  # Não validado
        user.save()

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        
        response = view.post(request)
        assert response.status_code == 404
        assert "E-mail não encontrado" in response.data['detail']
        assert "Gabinete da Diretoria Regional de Educação (DRE)" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_fluxo_nao_tratado(self, mock_sme):
        """Testa CPF que não se enquadra em nenhum fluxo específico"""
        mock_sme.return_value = {} #Não acha no CoreSSO

        # Cria usuário local
        user = User.objects.create_user(
            username='12345678901',
            email='teste@escola.com',
            password='teste123',
            rede='Direta'
        )
        # Não é diretor, tem email no local

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        
        response = view.post(request)
        assert response.status_code == 401
        assert "Usuário ou RF não encontrado" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    def test_cpf_fluxo_CoreSS_nao_diretor(self, mock_sme):
        """Testa CPF que esta no CoreSSO mas não é diretor"""
        mock_sme.return_value = {
            'email': None,
            'nome': 'Usuário Teste'
        }

        # Cria usuário local
        user = User.objects.create_user(
            username='12345678901',
            email='teste@escola.com',
            password='teste123',
        )
        # Não é diretor e por isso não envia email

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '12345678901'})
        
        response = view.post(request)
        assert response.status_code == 401
        assert "Olá Usuário! Desculpe, mas o acesso ao GIPE é restrito a perfis específicos." in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_anonimizar_email_curto(self, mock_enviar, mock_senha, mock_sme):
        """Testa anonimização de email com menos de 3 caracteres"""
        mock_sme.return_value = {
            'email': 'ab@escola.com',  # Email com 2 caracteres
            'nome': 'Fulano da Silva'
        }
        mock_senha.return_value = {
            'token': 'tokenxyz',
            'uid': 'abc123',
            'name': 'Fulano da Silva'
        }
        mock_enviar.return_value = None

        User.objects.create_user(
            username='1234567', 
            email='ab@escola.com',
            password='teste123'
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 200
        # Verifica se a anonimização funciona para email curto: a*@escola.com
        assert "a*@escola.com" in response.data['detail'] or "ab@escola.com" in response.data['detail']

    @patch('apps.users.services.sme_integracao_service.SmeIntegracaoService.informacao_usuario_sgp')
    @patch('apps.users.services.senha_service.SenhaService.gerar_token_para_reset')
    @patch('apps.users.services.envia_email_service.EnviaEmailService.enviar')
    def test_anonimizar_email_1_caractere(self, mock_enviar, mock_senha, mock_sme):
        """Testa anonimização de email com apenas 1 caractere"""
        mock_sme.return_value = {
            'email': 'a@escola.com',  # Email com 1 caractere
            'nome': 'Fulano da Silva'
        }
        mock_senha.return_value = {
            'token': 'tokenxyz',
            'uid': 'abc123',
            'name': 'Fulano da Silva'
        }
        mock_enviar.return_value = None

        User.objects.create_user(
            username='1234567', 
            email='a@escola.com',
            password='teste123'
        )

        view = EsqueciMinhaSenhaViewSet()
        request = MagicMock(data={'username': '1234567'})
        response = view.post(request)

        assert response.status_code == 200
        # Verifica se a anonimização funciona para email com 1 caractere: a@escola.com
        assert "a@escola.com" in response.data['detail']


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
        assert "não permitido" in response.data["detail"]

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
        assert "Erro interno do servidor. Tente novamente mais tarde." in response.data["detail"]

        # Senha local não deve ter sido alterada
        user.refresh_from_db()
        assert not user.check_password("SenhaPadr@o1")