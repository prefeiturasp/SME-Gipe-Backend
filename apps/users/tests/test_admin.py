import pytest
from http import HTTPStatus
from django.contrib import admin
from django.urls import reverse
from types import SimpleNamespace
from django import forms

from apps.users.models import User, Cargo
from apps.users.admin import (
    CustomUserCreationForm,
    CustomUserChangeForm,
    CustomAdminPasswordChangeForm,
    UserAdmin,
)


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

    def test_add_user(self, admin_client):
        url = reverse("admin:users_user_add")
        cargo = Cargo.objects.create(codigo=1, nome="Desenvolvedor")

        response = admin_client.post(
            url,
            data={
                "username": "test_user",
                "name": "Usuário Teste",
                "cpf": "12345678900",
                "cargo": cargo.pk,
                "password1": "My_R@ndom-P@ssw0rd1",
                "password2": "My_R@ndom-P@ssw0rd1",
                "is_active": True,
                "is_staff": True,
                "is_superuser": False,
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

    def test_valid_cpf(self):
        cargo = Cargo.objects.create(codigo=4, nome="Designer")

        form = CustomUserCreationForm(data={
            "username": "valido",
            "name": "Valido",
            "cpf": "12345678901",
            "cargo": cargo.pk,
            "password1": "Test1234@",
            "password2": "Test1234@",
        })

        assert form.is_valid()

    def test_invalid_cpf(self):
        cargo = Cargo.objects.create(codigo=2, nome="QA")

        form = CustomUserCreationForm(data={
            "username": "teste",
            "name": "Teste",
            "cpf": "ABC1234567",
            "cargo": cargo.pk,
            "password1": "Test1234@",
            "password2": "Test1234@",
        })

        assert not form.is_valid()
        assert 'cpf' in form.errors
        assert form.errors['cpf'] == ['CPF deve conter apenas números']


@pytest.mark.django_db
class TestCustomUserChangeForm:

    def test_valid_cpf(self):
        cargo = Cargo.objects.create(codigo=5, nome="Analista")
        user = User.objects.create_user(
            username="valido",
            name="Valido",
            cpf="98765432100",
            cargo=cargo,
            email="valido@example.com",
            password="Test1234@"
        )

        form = CustomUserChangeForm(
            data={
                "username": user.username,
                "nome": user.name,
                "name": user.name,
                "cpf": user.cpf,
                "cargo": cargo.pk,
                "email": user.email,
                "date_joined": user.date_joined,
            },
            instance=user
        )

        assert form.is_valid(), f"Form inválido com erros: {form.errors}"

    def test_invalid_cpf(self):
        cargo = Cargo.objects.create(codigo=3, nome="DevOps")

        form = CustomUserChangeForm(data={
            "username": "teste",
            "name": "Teste",
            "cpf": "A1B2C3",
            "cargo": cargo.pk,
        })

        assert not form.is_valid()
        assert 'cpf' in form.errors
        assert form.errors['cpf'] == ['CPF deve conter apenas números']


@pytest.mark.django_db
class TestCustomAdminPasswordChangeForm:

    def test_removes_usable_password_field(self):
        user = User.objects.create_user(
            username="admin_test",
            password="Test1234@"
        )

        form = CustomAdminPasswordChangeForm(user=user)
        form.fields['usable_password'] = forms.CharField()

        # Re-executa __init__ para testar se campo é removido
        form.__init__(user=user)

        assert 'usable_password' not in form.fields