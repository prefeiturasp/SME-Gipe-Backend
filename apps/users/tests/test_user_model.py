"""
Testes para o modelo User.
"""
import pytest
from django.utils import timezone
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


@pytest.mark.django_db
class TestUserModelCamposAprovacaoInativacao:
    """Testes para campos de aprovação e inativação do modelo User."""

    def test_campos_aprovacao_podem_ser_preenchidos(self):
        """Testa persistência dos campos de aprovação."""
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")
        data_aprovacao = timezone.now()

        user = User.objects.create(
            username="user_aprovado",
            cpf="12312312312",
            name="Usuário Aprovado",
            cargo=cargo,
            data_aprovacao=data_aprovacao,
            responsavel_aprovacao="ADMIN001",
        )

        user.refresh_from_db()

        assert user.data_aprovacao == data_aprovacao
        assert user.responsavel_aprovacao == "ADMIN001"

    def test_campos_inativacao_podem_ser_preenchidos(self):
        """Testa persistência dos campos de inativação."""
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")
        data_inativacao = timezone.now()

        user = User.objects.create(
            username="user_inativo",
            cpf="32132132132",
            name="Usuário Inativo",
            cargo=cargo,
            data_inativacao=data_inativacao,
            responsavel_inativacao="ADMIN002",
            is_active=False,
        )

        user.refresh_from_db()

        assert user.data_inativacao == data_inativacao
        assert user.responsavel_inativacao == "ADMIN002"
        assert user.is_active is False

    def test_campos_aprovacao_e_inativacao_podem_ser_nulos(self):
        """Testa que os campos permitem valores nulos."""
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")

        user = User.objects.create(
            username="user_sem_datas",
            cpf="99988877766",
            name="Usuário Sem Datas",
            cargo=cargo,
        )

        user.refresh_from_db()

        assert user.data_aprovacao is None
        assert user.responsavel_aprovacao is None
        assert user.data_inativacao is None
        assert user.responsavel_inativacao is None