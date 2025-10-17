import pytest
from rest_framework.test import APIRequestFactory
from rest_framework import status
from unittest.mock import patch, MagicMock
from apps.users.api.views.login_viewset import LoginView
from apps.helpers.exceptions import AuthenticationError
from django.db import IntegrityError, DatabaseError
from apps.users.models import User, Cargo


class TestLoginView:

    @patch("apps.users.services.cargos_service.CargosService.get_cargo_permitido")
    @patch("apps.users.services.cargos_service.CargosService.get_cargos")
    @patch("apps.users.services.login_service.AutenticacaoService.autentica")
    @patch("apps.users.api.views.login_viewset.LoginView.create_or_update_user_with_cargo")
    @patch("apps.users.api.views.login_viewset.LoginView._generate_token")
    def test_login_sucesso(self, mock_generate_token, mock_create_update, mock_autentica, mock_get_cargos, mock_get_cargo_permitido):
        mock_autentica.return_value = {
            "nome": "João Silva",
            "email": "joao@email.com",
            "cpf": "12345678901",
            "login": "joaos"
        }

        mock_get_cargos.return_value = {"cargos": [{"codigo": 30, "nome": "Diretor de Escola"}]}
        mock_get_cargo_permitido.return_value = {"codigo": 30, "nome": "Diretor de Escola"}

        user_mock = MagicMock()
        user_mock.cargo.codigo = 30
        user_mock.cargo.nome = "Diretor de Escola"
        mock_create_update.return_value = user_mock
        mock_generate_token.return_value = {'access': 'token-acesso', 'refresh': 'token-refresh'}

        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "1234567", "password": "senha123"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "João Silva"
        assert response.data["perfil_acesso"]["codigo"] == 30
        assert response.data["token"] == 'token-acesso'

    def test_login_sem_credenciais(self):
        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "", "password": ""}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Credenciais inválidas"

    @patch("apps.users.services.login_service.AutenticacaoService.autentica", side_effect=AuthenticationError("Credenciais inválidas"))
    def test_login_credenciais_invalidas(self, mock_autentica):
        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "1234567", "password": "senha_errada"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "Usuário e/ou senha inválida"

    @patch("apps.users.services.login_service.AutenticacaoService.autentica")
    @patch("apps.users.services.cargos_service.CargosService.get_cargos")
    @patch("apps.users.services.cargos_service.CargosService.get_cargo_permitido", return_value=None)
    @patch("apps.users.api.views.login_viewset.LoginView._get_cargo_gipe_ou_ponto_focal", return_value=None)
    def test_login_usuario_sem_cargo_permitido(self, mock_get_cargo_alt, mock_get_cargo_permitido, mock_get_cargos, mock_autentica):
        auth_data = {
            "nome": "Maria Souza",
            "email": "maria@email.com",
            "cpf": "98765432100",
            "login": "marias"
        }
        mock_autentica.return_value = auth_data
        mock_get_cargos.return_value = {"cargos": [{"codigo": 40, "nome": "Professor"}]}

        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "1234567", "password": "senha"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"].startswith("Olá Maria!")

    @patch("apps.users.services.login_service.AutenticacaoService.autentica", side_effect=Exception("Erro inesperado"))
    def test_erro_interno(self, mock_autentica):
        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "1234567", "password": "senha"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["detail"] == "Erro interno do sistema. Tente novamente mais tarde."


    @pytest.mark.django_db
    @patch("apps.users.models.User.objects.update_or_create")
    @patch("apps.users.models.User.objects.filter")
    @patch("apps.users.models.Cargo.objects.update_or_create")
    def test_create_or_update_user_with_cargo_success(self, mock_cargo_update_or_create, mock_user_filter, mock_user_update_or_create):
        mock_cargo = MagicMock()
        mock_cargo_update_or_create.return_value = (mock_cargo, True)

        mock_user = MagicMock()
        mock_user.check_password.return_value = False 
        mock_user_filter.return_value.first.return_value = mock_user
        mock_user_update_or_create.return_value = (mock_user, True)

        view = LoginView()

        senha = "senha123"
        auth_data = {
            "login": "usuario1",
            "nome": "Usuário Teste",
            "numeroDocumento": "12345678901",
            "email": "usuario@email.com",
        }
        cargo_data = {
            "codigo": 99,
            "nome": "Cargo Teste",
        }

        user = view.create_or_update_user_with_cargo(auth_data["login"], senha, auth_data, cargo_data)

        assert user == mock_user
        mock_cargo_update_or_create.assert_called_once_with(
            codigo=99, defaults={"nome": "Cargo Teste"}
        )
        mock_user_filter.assert_called_once_with(username="usuario1")
        mock_user_update_or_create.assert_called_once()


    @patch("apps.users.models.Cargo.objects.update_or_create", side_effect=Exception("Erro inesperado no DB"))
    def test_create_or_update_user_with_cargo_db_error(self, mock_cargo_update_or_create):
        view = LoginView()
        senha = "senha123"
        auth_data = {
            "login": "usuario1",
            "nome": "Usuário Teste",
            "cpf": "12345678901",
            "email": "usuario@email.com"
        }
        cargo_data = {
            "codigo": 99,
            "nome": "Cargo Teste"
        }

        with pytest.raises(Exception) as excinfo:
            view.create_or_update_user_with_cargo(auth_data["login"], senha, auth_data, cargo_data)

        assert "Ocorreu um erro inesperado" in str(excinfo.value)

    @pytest.mark.django_db
    @patch("apps.users.api.views.login_viewset.User.objects.update_or_create")
    @patch("apps.users.api.views.login_viewset.Cargo.objects.update_or_create")
    def test_create_or_update_user_with_cargo_integrity_error(self, mock_cargo_update_or_create, mock_user_update_or_create):
        mock_cargo_update_or_create.side_effect = IntegrityError("Integrity error")

        view = LoginView()
        senha = "senha123"
        auth_data = {
            "login": "usuario1",
            "nome": "Usuário Teste",
            "cpf": "12345678901",
            "email": "usuario@email.com"
        }
        cargo_data = {
            "codigo": 99,
            "nome": "Cargo Teste"
        }

        with pytest.raises(Exception) as excinfo:
            view.create_or_update_user_with_cargo(auth_data["login"], senha, auth_data, cargo_data)

        assert "Erro de integridade ao salvar os dados" in str(excinfo.value)

    @pytest.mark.django_db
    @patch("apps.users.api.views.login_viewset.User.objects.update_or_create")
    @patch("apps.users.api.views.login_viewset.Cargo.objects.update_or_create")
    def test_create_or_update_user_with_cargo_database_error(self, mock_cargo_update_or_create, mock_user_update_or_create):
        mock_cargo_update_or_create.side_effect = DatabaseError("Database error")

        view = LoginView()
        senha = "senha123"
        auth_data = {
            "login": "usuario1",
            "nome": "Usuário Teste",
            "cpf": "12345678901",
            "email": "usuario@email.com"
        }
        cargo_data = {
            "codigo": 99,
            "nome": "Cargo Teste"
        }

        with pytest.raises(Exception) as excinfo:
            view.create_or_update_user_with_cargo(auth_data["login"], senha, auth_data, cargo_data)

        assert "Erro no banco de dados" in str(excinfo.value)

    @pytest.mark.django_db
    @patch("apps.users.api.views.login_viewset.User.objects.update_or_create")
    @patch("apps.users.api.views.login_viewset.Cargo.objects.update_or_create")
    def test_create_or_update_user_with_cargo_unexpected_error(self, mock_cargo_update_or_create, mock_user_update_or_create):
        mock_cargo_update_or_create.side_effect = Exception("Unexpected error")

        view = LoginView()
        senha = "senha123"
        auth_data = {
            "login": "usuario1",
            "nome": "Usuário Teste",
            "cpf": "12345678901",
            "email": "usuario@email.com"
        }
        cargo_data = {
            "codigo": 99,
            "nome": "Cargo Teste"
        }

        with pytest.raises(Exception) as excinfo:
            view.create_or_update_user_with_cargo(auth_data["login"], senha, auth_data, cargo_data)

        assert "Ocorreu um erro inesperado" in str(excinfo.value)

    def test_generate_token(self):
        view = LoginView()

        mock_user = MagicMock()
        mock_user.username = "testeuser"
        mock_user.name = "Teste Usuário"

        mock_cargo = MagicMock()
        mock_cargo.codigo = 123
        mock_cargo.nome = "Coordenador"
        mock_user.cargo = mock_cargo

        mock_refresh = {}
        mock_refresh_obj = MagicMock(spec=dict)
        mock_refresh_obj.__setitem__.side_effect = mock_refresh.__setitem__
        mock_refresh_obj.__getitem__.side_effect = mock_refresh.__getitem__
        mock_refresh_obj.__str__.return_value = "refresh-token"

        mock_access = {}
        mock_access_obj = MagicMock(spec=dict)
        mock_access_obj.__setitem__.side_effect = mock_access.__setitem__
        mock_access_obj.__getitem__.side_effect = mock_access.__getitem__
        mock_access_obj.__str__.return_value = "access-token"

        mock_refresh_obj.access_token = mock_access_obj

        with patch('apps.users.api.views.login_viewset.RefreshToken.for_user', return_value=mock_refresh_obj):
            tokens = view._generate_token(mock_user)

        assert tokens == {'access': 'access-token', 'refresh': 'refresh-token'}

        assert mock_refresh["perfil_codigo"] == 123
        assert mock_refresh["perfil_nome"] == "Coordenador"
        assert mock_access["perfil_codigo"] == 123
        assert mock_access["perfil_nome"] == "Coordenador"

    @patch("apps.users.services.login_service.AutenticacaoService.autentica")
    @patch("apps.users.services.cargos_service.CargosService.get_cargos")
    @patch("apps.users.services.cargos_service.CargosService.get_cargo_permitido", return_value=None)
    @patch("apps.users.api.views.login_viewset.LoginView._get_cargo_gipe_ou_ponto_focal")
    @patch("apps.users.api.views.login_viewset.LoginView.create_or_update_user_with_cargo")
    @patch("apps.users.api.views.login_viewset.LoginView._generate_token")
    def test_login_com_cargo_alternativo_gipe_ou_ponto_focal(self, mock_generate_token, mock_create_update, mock_get_cargo_alt, mock_get_cargo_permitido, mock_get_cargos, mock_autentica):
        auth_data = {
            "nome": "Carlos Dias",
            "email": "carlos@email.com",
            "cpf": "11122233344",
            "login": "carlosd"
        }
        mock_autentica.return_value = auth_data
        mock_get_cargos.return_value = {"cargos": [{"codigo": 40, "nome": "Outro Cargo"}]}
        mock_get_cargo_alt.return_value = {"codigo": 0, "nome": "GIPE"}

        user_mock = MagicMock()
        user_mock.cargo.codigo = 0
        user_mock.cargo.nome = "GIPE"
        mock_create_update.return_value = user_mock
        mock_generate_token.return_value = {'access': 'token-acesso', 'refresh': 'token-refresh'}

        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "1234567", "password": "senha"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["perfil_acesso"]["nome"] == "GIPE"
        assert response.data["token"] == "token-acesso"

    @patch("apps.users.services.login_service.AutenticacaoService.autentica")
    @patch("apps.users.services.cargos_service.CargosService.get_cargos")
    @patch("apps.users.services.cargos_service.CargosService.get_cargo_permitido", return_value=None)
    @patch("apps.users.api.views.login_viewset.LoginView._get_cargo_gipe_ou_ponto_focal", return_value=None)
    @patch("apps.users.services.cargos_service.CargosService.get_cargo_perfil_guide")
    @patch("apps.users.api.views.login_viewset.LoginView.create_or_update_user_with_cargo")
    @patch("apps.users.api.views.login_viewset.LoginView._generate_token")
    def test_login_com_perfil_diretor_escola(self, mock_generate_token, mock_create_update, mock_get_cargo_perfil_guide, mock_get_cargo_gipe_ou_ponto_focal, mock_get_cargo_permitido, mock_get_cargos, mock_autentica):
        auth_data = {
            "nome": "Ana Paula",
            "email": "ana@email.com",
            "cpf": "00011122233",
            "login": "anapaula",
            "perfis": ["DIRETOR DE ESCOLA"],
        }

        mock_autentica.return_value = auth_data
        mock_get_cargos.return_value = {"cargos": [{"codigo": 50, "nome": "Outro Cargo"}]}
        mock_get_cargo_perfil_guide.return_value = {"codigo": 3360, "nome": "DIRETOR DE ESCOLA"}

        user_mock = MagicMock()
        user_mock.cargo.codigo = 3360
        user_mock.cargo.nome = "DIRETOR DE ESCOLA"
        mock_create_update.return_value = user_mock
        mock_generate_token.return_value = {'access': 'token-acesso', 'refresh': 'token-refresh'}

        factory = APIRequestFactory()
        request = factory.post("/api/login", {"username": "1234567", "password": "senha"}, format='json')

        response = LoginView.as_view()(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["perfil_acesso"]["nome"] == "DIRETOR DE ESCOLA"
        assert response.data["token"] == "token-acesso"


class TestCargoAlternativo:

    def setup_method(self):
        self.view = LoginView()

    @pytest.mark.django_db
    def test_get_cargo_gipe_ou_ponto_focal_sucesso(self):
        cargo_real = Cargo.objects.create(nome='GIPE', codigo=0)
        usuario = User.objects.create_user(username='testeuser', password='teste123')
        usuario.cargo = cargo_real
        usuario.save()

        view = LoginView()
        with patch("apps.users.api.views.login_viewset.User.objects.get", return_value=usuario):
            result = view._get_cargo_gipe_ou_ponto_focal('testeuser')

        assert result == {'codigo': 0, 'nome': 'GIPE'}

    @pytest.mark.django_db
    def test_get_cargo_gipe_ou_ponto_focal_nao_encontrado(self):
        view = LoginView()
        with patch("apps.users.api.views.login_viewset.User.objects.get", side_effect=User.DoesNotExist):
            result = view._get_cargo_gipe_ou_ponto_focal('naoexiste')

        assert result is None

    @pytest.mark.django_db
    def test_get_cargo_gipe_ou_ponto_focal_usuario_sem_cargo_valido(self):
        cargo_real = Cargo.objects.create(nome='Outro Cargo', codigo=2)
        usuario = User.objects.create_user(username='usuario', password='teste123')
        usuario.cargo = cargo_real
        usuario.save()

        view = LoginView()
        with patch("apps.users.api.views.login_viewset.User.objects.get", return_value=usuario):
            result = view._get_cargo_gipe_ou_ponto_focal('usuario')

        assert result is None