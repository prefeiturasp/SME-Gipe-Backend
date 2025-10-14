import pytest
from apps.alteracao_email.models.alteracao_email import AlteracaoEmail


@pytest.mark.django_db
def test_str_retorna_usuario_e_novo_email(django_user_model):
    usuario = django_user_model.objects.create_user(
        username="testeuser", email="teste@abc.com.br", password="123456"
    )
    solicitacao = AlteracaoEmail.objects.create(
        usuario=usuario,
        novo_email="novo@abc.com.br"
    )

    resultado = str(solicitacao)

    assert resultado == "testeuser -> novo@abc.com.br"