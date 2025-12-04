import secrets
import pytest
from django.contrib.auth import get_user_model
from rest_framework.serializers import ValidationError
from apps.unidades.models.unidades import Unidade, TipoGestaoChoices
from apps.users.api.serializers.usuario_serializer import UserCreateSerializer
from apps.users.models import Cargo
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def cargo():
    return Cargo.objects.create(codigo=9999, nome="Gestor")


@pytest.fixture
def unidade():
    return Unidade.objects.create(nome="Unidade Teste")


@pytest.fixture
def user_data(unidade, cargo):
    pwd = secrets.token_urlsafe(16)
    return {
        'username': 'novousuario',
        'password': pwd,
        'name': 'Novo Usuário',
        'email': 'novo@sme.prefeitura.sp.gov.br',
        'cpf': '12345678901',
        'cargo': cargo.pk,
        'unidades': [unidade.uuid],
        'rede': TipoGestaoChoices.DIRETA,
    }


@pytest.fixture
def existing_user(cargo):
    pwd = secrets.token_urlsafe(16)
    user = User.objects.create_user(username='usuarioexistente')
    user.set_password(pwd)
    user.cargo = cargo
    user.name = 'Usuário Existente'
    user.email = 'existente@sme.prefeitura.sp.gov.br'
    user.cpf = '11122233344'
    user.rede = TipoGestaoChoices.DIRETA
    user.save()
    return user


@pytest.fixture
def api_client(existing_user):
    def _create(user=None):
        if not user:
            pwd = secrets.token_urlsafe(16)
            user = User.objects.create_user(username="tester")
            user.set_password(pwd)
            user.save()
        client = APIClient()
        client.force_authenticate(user=user)
        return client
    return _create


@pytest.mark.django_db
class TestUserCreateSerializer:

    def test_create_valid_user(self, user_data):
        user_data['cpf'] = '123.456.789-01'
        serializer = UserCreateSerializer(data=user_data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.username == user_data['username']
        assert user.unidades.count() == 1
        assert user.is_validado is False

    def test_invalid_cpf_length(self, user_data):
        user_data['cpf'] = '123'
        serializer = UserCreateSerializer(data=user_data)
        assert not serializer.is_valid()
        assert serializer.errors['field'] == 'cpf'
        assert serializer.errors['detail'] == 'CPF inválido.'

    def test_invalid_cpf_repeated_digits(self, user_data):
        user_data['cpf'] = '11111111111'
        serializer = UserCreateSerializer(data=user_data)
        assert not serializer.is_valid()
        assert serializer.errors['field'] == 'cpf'
        assert serializer.errors['detail'] == 'CPF inválido.'

    def test_duplicate_cpf(self, user_data, existing_user):
        user_data['cpf'] = existing_user.cpf
        user_data['username'] = 'outro_nome'
        serializer = UserCreateSerializer(data=user_data)
        assert not serializer.is_valid()
        assert serializer.errors['field'] == 'cpf'
        assert serializer.errors['detail'] == 'Já existe uma conta com este CPF.'

    def test_duplicate_email(self, user_data, existing_user):
        user_data['email'] = existing_user.email
        user_data['username'] = 'outro_nome'
        serializer = UserCreateSerializer(data=user_data)
        assert not serializer.is_valid()
        assert serializer.errors['field'] == 'email'
        assert serializer.errors['detail'] == 'Este e-mail já está cadastrado.'

    def test_invalid_email_domain(self, user_data):
        user_data['email'] = 'teste@dominio.com'
        serializer = UserCreateSerializer(data=user_data)
        assert not serializer.is_valid()
        assert serializer.errors['field'] == 'email'
        assert serializer.errors['detail'] == 'Utilize seu e-mail institucional.'

    def test_is_valid_with_raise_exception(self, user_data):
        user_data['cpf'] = '123'
        serializer = UserCreateSerializer(data=user_data)
        with pytest.raises(ValidationError) as exc_info:
            serializer.is_valid(raise_exception=True)
        assert exc_info.value.detail['field'] == 'cpf'
        assert exc_info.value.detail['detail'] == 'CPF inválido.'