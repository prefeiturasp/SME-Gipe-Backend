import pytest
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError

from apps.users.models import User
from apps.alteracao_email.api.serializers.alteracao_email_serializer import AlteracaoEmailSerializer


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="teste",
        email="usuario@sme.prefeitura.sp.gov.br",
        password="senha123",
        cpf="12345678900",
    )


@pytest.fixture
def request_factory():
    return APIRequestFactory()


@pytest.mark.django_db
class TestAlteracaoEmailSerializer:

    def get_serializer(self, user, email):
        request = APIRequestFactory().get("/")
        request.user = user
        serializer = AlteracaoEmailSerializer(
            data={"new_email": email},
            context={"request": request},
        )
        return serializer

    def test_valid_email(self, user):

        serializer = self.get_serializer(user, "novo_email@sme.prefeitura.sp.gov.br")

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["new_email"] == "novo_email@sme.prefeitura.sp.gov.br"

    def test_email_igual_ao_atual(self, user):

        serializer = self.get_serializer(user, user.email)

        assert not serializer.is_valid()
        assert "O novo e-mail não pode ser igual ao atual." in str(serializer.errors)

    def test_email_com_dominio_invalido(self, user):

        serializer = self.get_serializer(user, "novo@gmail.com")

        assert not serializer.is_valid()
        assert serializer.errors["detail"] == "Utilize seu e-mail institucional."

    def test_email_ja_em_uso(self, user):

        User.objects.create_user(
            username="outro",
            email="existente@sme.prefeitura.sp.gov.br",
            password="senha456",
            cpf="98765432100",
        )

        serializer = self.get_serializer(user, "existente@sme.prefeitura.sp.gov.br")

        assert not serializer.is_valid()
        assert serializer.errors["detail"] == "Este e-mail já está cadastrado."

    def test_formato_de_email_invalido(self, user):

        email_invalido = "novo@gmail.com@"
        serializer = self.get_serializer(user, email_invalido)

        assert not serializer.is_valid()
        assert str(serializer.errors["detail"]) == "Utilize seu e-mail institucional."

    def test_campo_obrigatorio(self, request_factory, user):

        request = request_factory.get("/")
        request.user = user
        serializer = AlteracaoEmailSerializer(
            data={},
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "O campo de e-mail é obrigatório." in str(serializer.errors)

    def test_formato_de_email_invalido_forca_except(self, user):

        email_invalido = "invalido@@sme.prefeitura.sp.gov.br"
        serializer = self.get_serializer(user, email_invalido)

        assert not serializer.is_valid()
        assert serializer.errors["detail"] == "Digite um e-mail válido!"

    def test_is_valid_raise_exception(self, user):

        serializer = self.get_serializer(user, "novo@gmail.com")

        with pytest.raises(ValidationError) as exc_info:
            serializer.is_valid(raise_exception=True)

        first_message = str(exc_info.value.detail["detail"])
        assert first_message == "Utilize seu e-mail institucional."