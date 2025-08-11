import pytest
from django.contrib.auth import get_user_model
from apps.unidades.models.unidades import Unidade, TipoGestaoChoices
from apps.users.api.serializers.registrar_usuario_serializer import UserCreateSerializer
from apps.users.models import Cargo

User = get_user_model()


@pytest.fixture
def cargo():
    return Cargo.objects.create(codigo=9999, nome="Gestor")


@pytest.fixture
def unidade():
    return Unidade.objects.create(nome="Unidade Teste")


@pytest.fixture
def user_data(unidade, cargo):
    return {
        'username': 'novousuario',
        'password': 'senha123',
        'name': 'Novo Usuário',
        'email': 'novo@teste.com',
        'cpf': '12345678901',
        'cargo': cargo.pk,
        'unidades': [unidade.uuid],
        'rede': TipoGestaoChoices.DIRETA,
    }


@pytest.fixture
def existing_user(cargo):
    return User.objects.create_user(
        username='usuarioexistente',
        password='senha123',
        name='Usuário Existente',
        email='existente@teste.com',
        cpf='11122233344',
        cargo=cargo,
        rede=TipoGestaoChoices.DIRETA,
    )


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
        assert 'cpf' in serializer.errors

    def test_invalid_cpf_repeated_digits(self, user_data):
        user_data['cpf'] = '11111111111'
        serializer = UserCreateSerializer(data=user_data)
        assert not serializer.is_valid()
        assert 'cpf' in serializer.errors

    def test_duplicate_cpf(self, user_data, existing_user):
        user_data['cpf'] = existing_user.cpf
        user_data['username'] = 'outro_nome'
        serializer = UserCreateSerializer(data=user_data)
        assert not serializer.is_valid()
        assert 'cpf' in serializer.errors