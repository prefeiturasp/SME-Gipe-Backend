"""
Testes para o modelo User.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.users.models import Cargo

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Testes para propriedades do modelo User."""

    def test_is_diretor_retorna_true_quando_cargo_codigo_eh_3360(self):
        """
        Testa que is_diretor retorna True quando o usuário tem cargo com código 3360.
        """
        # Arrange
        cargo_diretor = Cargo.objects.create(codigo=3360, nome="Diretor")
        user = User.objects.create(
            username="diretor_teste",
            cpf="12345678901",
            name="Diretor Teste",
            cargo=cargo_diretor
        )

        # Act & Assert
        assert user.is_diretor is True

    def test_is_diretor_retorna_false_quando_cargo_codigo_diferente(self):
        """
        Testa que is_diretor retorna False quando o usuário tem cargo com código diferente de 3360.
        """
        # Arrange
        cargo_outro = Cargo.objects.create(codigo=9999, nome="Outro Cargo")
        user = User.objects.create(
            username="outro_teste",
            cpf="98765432109",
            name="Outro Teste",
            cargo=cargo_outro
        )

        # Act & Assert
        assert user.is_diretor is False

    def test_is_diretor_retorna_false_quando_cargo_sem_codigo(self):
        """
        Testa que is_diretor retorna False quando o cargo não tem código definido.
        """
        # Arrange
        cargo_sem_codigo = Cargo.objects.create(codigo=5000, nome="Cargo Teste")
        user = User.objects.create(
            username="user_teste",
            cpf="11122233344",
            name="User Teste",
            cargo=cargo_sem_codigo
        )
        
        # Força cargo.codigo a ser None para testar o edge case
        user.cargo.codigo = None

        # Act & Assert
        assert user.is_diretor is False
