import pytest
from http import HTTPStatus
from django.contrib import admin
from django.urls import reverse
from types import SimpleNamespace
from django import forms
from unittest.mock import patch, ANY

from apps.users.models import User, Cargo
from apps.users.admin import (
    CustomUserCreationForm,
    CustomUserChangeForm,
    CustomAdminPasswordChangeForm,
    UserAdmin,
)

from apps.unidades.models.unidades import TipoGestaoChoices
from apps.helpers.exceptions import CargaUsuarioException


@pytest.fixture
def cargo():
    return Cargo.objects.create(codigo=1, nome="Desenvolvedor")


@pytest.mark.django_db
class TestUserAdmin:

    def test_changelist_view(self, admin_client):
        url = reverse("admin:users_user_changelist")
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK

    def test_search_user(self, admin_client):
        url = reverse("admin:users_user_changelist")
        response = admin_client.get(url, data={"q": "test"})
        assert response.status_code == HTTPStatus.OK

    def test_add_user(self, admin_client, cargo):
        url = reverse("admin:users_user_add")

        response = admin_client.post(
            url,
            data={
                "username": "test_user",
                "name": "Usuário Teste",
                "cpf": "12345678900",
                "cargo": cargo.pk,
                "rede": TipoGestaoChoices.DIRETA.value,
                "unidades": [],
                "password1": "My_R@ndom-P@ssw0rd1",
                "password2": "My_R@ndom-P@ssw0rd1",
                "is_active": True,
                "is_staff": True,
                "is_superuser": False,
                "is_validado": True,
            },
            follow=True,
        )

        assert response.status_code == HTTPStatus.OK
        assert User.objects.filter(username="test_user").exists()

    def test_view_user_detail(self, admin_client):
        user = User.objects.get(username="admin")
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK
        assert b'is_validado' in response.content

    def test_get_readonly_fields_for_superuser(self):
        admin_instance = UserAdmin(User, admin.site)
        request = SimpleNamespace(user=User(is_superuser=True))
        fields = admin_instance.get_readonly_fields(request)
        assert 'is_superuser' not in fields

    def test_get_readonly_fields_for_non_superuser(self):
        admin_instance = UserAdmin(User, admin.site)
        request = SimpleNamespace(user=User(is_superuser=False))
        fields = admin_instance.get_readonly_fields(request)
        assert 'is_superuser' in fields


@pytest.mark.django_db
class TestCargoAdmin:

    def test_change_view_accessible(self, admin_client):
        cargo = Cargo.objects.create(codigo=6, nome="Engenheiro")
        url = reverse("admin:users_cargo_change", kwargs={"object_id": cargo.pk})
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
class TestCustomUserCreationForm:

    def test_valid_cpf(self, cargo):
        form = CustomUserCreationForm(data={
            "username": "valido",
            "name": "Valido",
            "cpf": "12345678901",
            "cargo": cargo.pk,
            "rede": TipoGestaoChoices.DIRETA.value,
            "unidades": [],
            "password1": "Test1234@",
            "password2": "Test1234@",
            "is_validado": True,
        })

        assert form.is_valid(), f"Form inválido com erros: {form.errors}"

    def test_invalid_cpf(self, cargo):
        form = CustomUserCreationForm(data={
            "username": "teste",
            "name": "Teste",
            "cpf": "ABC1234567",
            "cargo": cargo.pk,
            "rede": TipoGestaoChoices.DIRETA.value,
            "unidades": [],
            "password1": "Test1234@",
            "password2": "Test1234@",
            "is_validado": True,
        })

        assert not form.is_valid()
        assert 'cpf' in form.errors
        assert form.errors['cpf'] == ['CPF deve conter apenas números']


@pytest.mark.django_db
class TestCustomUserChangeForm:

    def test_valid_cpf(self, cargo):
        user = User.objects.create_user(
            username="valido",
            name="Valido",
            cpf="98765432100",
            cargo=cargo,
            email="valido@example.com",
            rede="DIRETA",
            password="Test1234@",
            is_validado=True
        )

        form = CustomUserChangeForm(
            data={
                "username": user.username,
                "name": user.name,
                "cpf": user.cpf,
                "cargo": cargo.pk,
                "email": user.email,
                "rede": "DIRETA",
                "unidades": [],
                "date_joined": user.date_joined,
                "last_login": user.last_login,
                "is_validado": True,
            },
            instance=user
        )

        assert form.is_valid(), f"Form inválido com erros: {form.errors}"

    def test_invalid_cpf(self, cargo):
        user = User.objects.create_user(
            username="teste",
            name="Teste",
            cpf="12345678900",
            cargo=cargo,
            rede="INDIRETA",
            password="Test1234@",
            is_validado=True
        )

        form = CustomUserChangeForm(
            data={
                "username": user.username,
                "name": user.name,
                "cpf": "A1B2C3",
                "cargo": cargo.pk,
                "email": "teste@example.com",
                "rede": "INDIRETA",
                "unidades": [],
                "date_joined": user.date_joined,
                "last_login": user.last_login,
                "is_validado": True,
            },
            instance=user
        )

        assert not form.is_valid()
        assert 'cpf' in form.errors
        assert form.errors['cpf'] == ['CPF deve conter apenas números']


@pytest.mark.django_db
class TestCustomAdminPasswordChangeForm:

    def test_removes_usable_password_field(self):
        user = User.objects.create_user(
            username="admin_test",
            password="Test1234@",
            is_validado=True
        )

        form = CustomAdminPasswordChangeForm(user=user)
        form.fields['usable_password'] = forms.CharField()

        # Re-executa __init__ para testar se campo é removido
        form.__init__(user=user)

        assert 'usable_password' not in form.fields


@pytest.mark.django_db
class TestEnviarParaCoreSSOAction:

    def test_render_confirmation_template(self, admin_client, cargo):
        user = User.objects.create_user(
            username="user1",
            name="User 1",
            cpf="12345678901",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
        )
        url = reverse("admin:users_user_changelist")
        data = {
            "action": "enviar_para_core_sso",
            "_selected_action": [user.pk],
        }
        response = admin_client.post(url, data)
        # Verifica se o template correto foi usado
        template_names = [t.name for t in response.templates if t.name]

        assert response.status_code == 200
        assert any("confirm_enviar_core_sso.html" in name for name in template_names)

    @patch("apps.users.services.envia_email_service.EnviaEmailService.enviar", return_value=None)
    @patch("apps.users.admin.CriaUsuarioCoreSSOService.cria_usuario_core_sso", return_value=None)
    def test_action_with_valid_users(self, mock_cria_core_sso, mock_enviar_email, admin_client, cargo):
        user = User.objects.create_user(
            username="user_valid",
            name="User Valid",
            cpf="12345678902",
            email="valid@exemplo.com",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
        )

        url = reverse("admin:users_user_changelist")
        data = {
            "action": "enviar_para_core_sso",
            "_selected_action": [user.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)
        messages = [str(m) for m in response.context["messages"]]

        assert response.status_code == 200
        assert any("usuário(s) registrado(s) com sucesso no CoreSSO!" in m for m in messages)

        mock_enviar_email.assert_called_once_with(
            destinatario=user.email,
            assunto="Seu acesso ao GIPE foi aprovado!",
            template_html="emails/cadastro_aprovado.html",
            contexto={
                "nome_usuario": user.name,
                "aplicacao_url": ANY,
                "senha": ANY,
            },
        )

    def test_action_with_invalid_users(self, admin_client, cargo):
        user = User.objects.create_user(
            username="user_invalid",
            name="User Invalid",
            cpf="12345678903",
            cargo=cargo,
            rede=TipoGestaoChoices.DIRETA,
            password="Test1234@",
            is_validado=False,
        )
        url = reverse("admin:users_user_changelist")
        data = {
            "action": "enviar_para_core_sso",
            "_selected_action": [user.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)

        assert response.status_code == 200
        assert any("usuário(s). É necessário cumprir todos os requisitos." in str(m) for m in response.context["messages"])

    @patch("apps.users.services.envia_email_service.EnviaEmailService.enviar", return_value=None)
    @patch("apps.users.admin.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
    def test_action_with_mixed_users(self, mock_cria_core_sso, mock_enviar_email, admin_client, cargo):
        def side_effect(dados_usuario):
            if dados_usuario["login"] == "user_valid":
                return None
            raise CargaUsuarioException("Erro no CoreSSO")

        mock_cria_core_sso.side_effect = side_effect

        user_valid = User.objects.create_user(
            username="user_valid",
            name="User Valid",
            cpf="12345678902",
            email="valid@exemplo.com",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
        )

        user_invalid = User.objects.create_user(
            username="user_invalid",
            name="User Invalid",
            cpf="12345678903",
            email="invalid@exemplo.com",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
        )

        url = reverse("admin:users_user_changelist")
        data = {
            "action": "enviar_para_core_sso",
            "_selected_action": [user_valid.pk, user_invalid.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)
        messages = [str(m) for m in response.context["messages"]]

        assert response.status_code == 200
        assert any("usuário(s) registrado(s) com sucesso no CoreSSO!" in m for m in messages)
        assert any("user_invalid: Erro no CoreSSO" in m for m in messages)

        mock_enviar_email.assert_called_once_with(
            destinatario=user_valid.email,
            assunto="Seu acesso ao GIPE foi aprovado!",
            template_html="emails/cadastro_aprovado.html",
            contexto={
                "nome_usuario": user_valid.name,
                "aplicacao_url": ANY,
                "senha": ANY,
            },
        )
    
    @patch("apps.users.admin.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
    def test_action_gera_erro_carga_usuario_exception(self, mock_cria_core_sso, admin_client, cargo):
        mock_cria_core_sso.side_effect = CargaUsuarioException("Falha simulada")

        user = User.objects.create_user(
            username="user_erro",
            name="User Erro",
            cpf="12345678906",
            cargo=cargo,
            rede="INDIRETA",
            password="Test1234@",
            is_validado=True,
        )

        url = reverse("admin:users_user_changelist")
        data = {
            "action": "enviar_para_core_sso",
            "_selected_action": [user.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)

        messages_text = [str(m) for m in response.context["messages"]]

        assert any("Falha simulada" in m for m in messages_text)
        assert response.status_code == 200
        
@pytest.mark.django_db
class TestRemoverDoCoreSSOAction:

    def test_render_confirmation_template(self, admin_client, cargo):
        user = User.objects.create_user(
            username="user1",
            name="User 1",
            cpf="12345678901",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
            is_core_sso=True,
        )
        url = reverse("admin:users_user_changelist")
        data = {
            "action": "remover_do_core_sso",
            "_selected_action": [user.pk],
        }
        response = admin_client.post(url, data)
        template_names = [t.name for t in response.templates if t.name]

        assert response.status_code == 200
        assert any("confirm_remover_core_sso.html" in name for name in template_names)

    @patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService.remover_perfil_usuario_core_sso", return_value=None)
    def test_action_with_valid_users(self, mock_remover, admin_client, cargo):
        user = User.objects.create_user(
            username="user_valid",
            name="User Valid",
            cpf="12345678902",
            email="valid@exemplo.com",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
            is_core_sso=True,
        )

        url = reverse("admin:users_user_changelist")
        data = {
            "action": "remover_do_core_sso",
            "_selected_action": [user.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)
        messages = [str(m) for m in response.context["messages"]]

        assert response.status_code == 200
        assert any("perfil(is) removido(s) do CoreSSO com sucesso!" in m for m in messages)

        mock_remover.assert_called_once_with(
            login=user.username,
        )

    def test_action_with_invalid_users(self, admin_client, cargo):
        user = User.objects.create_user(
            username="user_invalid",
            name="User Invalid",
            cpf="12345678903",
            cargo=cargo,
            rede=TipoGestaoChoices.DIRETA,
            password="Test1234@",
            is_validado=False,
            is_core_sso=False,
        )
        url = reverse("admin:users_user_changelist")
        data = {
            "action": "remover_do_core_sso",
            "_selected_action": [user.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)

        assert response.status_code == 200
        assert any("Só é possível remover perfis de usuários da rede INDIRETA" in str(m) for m in response.context["messages"])

    @patch("apps.users.admin.CriaUsuarioCoreSSOService.remover_perfil_usuario_core_sso")
    def test_action_with_mixed_users(self, mock_remover, admin_client, cargo):
        def side_effect(login):
            if login == "user_valid":
                return None
            raise CargaUsuarioException("Erro simulado ao remover")

        mock_remover.side_effect = side_effect

        user_valid = User.objects.create_user(
            username="user_valid",
            name="User Valid",
            cpf="12345678902",
            email="valid@exemplo.com",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
            is_core_sso=True,
        )

        user_invalid = User.objects.create_user(
            username="user_invalid",
            name="User Invalid",
            cpf="12345678903",
            email="invalid@exemplo.com",
            cargo=cargo,
            rede=TipoGestaoChoices.INDIRETA,
            password="Test1234@",
            is_validado=True,
            is_core_sso=True,
        )

        url = reverse("admin:users_user_changelist")
        data = {
            "action": "remover_do_core_sso",
            "_selected_action": [user_valid.pk, user_invalid.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)
        messages = [str(m) for m in response.context["messages"]]

        assert response.status_code == 200
        assert any("perfil(is) removido(s) do CoreSSO com sucesso!" in m for m in messages)
        assert any("user_invalid: Erro simulado ao remover" in m for m in messages)

    @patch("apps.users.admin.CriaUsuarioCoreSSOService.remover_perfil_usuario_core_sso")
    def test_action_gera_erro_carga_usuario_exception(self, mock_remover, admin_client, cargo):
        mock_remover.side_effect = CargaUsuarioException("Falha simulada")

        user = User.objects.create_user(
            username="user_erro",
            name="User Erro",
            cpf="12345678906",
            cargo=cargo,
            rede="INDIRETA",
            password="Test1234@",
            is_validado=True,
            is_core_sso=True,
        )

        url = reverse("admin:users_user_changelist")
        data = {
            "action": "remover_do_core_sso",
            "_selected_action": [user.pk],
            "confirm": "yes",
        }

        response = admin_client.post(url, data, follow=True)

        messages_text = [str(m) for m in response.context["messages"]]

        assert any("Falha simulada" in m for m in messages_text)
        assert response.status_code == 200
