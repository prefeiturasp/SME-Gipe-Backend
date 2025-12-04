import secrets
import pytest
from apps.alteracao_email.models.alteracao_email import AlteracaoEmail


@pytest.fixture
def user_factory(django_user_model):
    def _create_user(username="testeuser", email="teste@abc.com.br"):
        pwd = secrets.token_urlsafe(16)
        user = django_user_model.objects.create_user(
            username=username,
            email=email,
        )
        user.set_password(pwd)
        user.save()
        return user

    return _create_user


@pytest.mark.django_db
def test_str_retorna_usuario_e_novo_email(user_factory):
    usuario = user_factory(
        username="testeuser",
        email="teste@abc.com.br",
    )

    solicitacao = AlteracaoEmail.objects.create(
        usuario=usuario,
        novo_email="novo@abc.com.br",
    )

    resultado = str(solicitacao)

    assert resultado == "testeuser -> novo@abc.com.br"