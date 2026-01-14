import pytest
import secrets

from unittest.mock import patch
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.unidades.services.gestao_unidade_service import InativarUnidadeService

@pytest.fixture
def usuario_vinculado_unidade(db, escola_sp):
    pwd = secrets.token_urlsafe(16)
    usuario = User.objects.create(
        username="usuario_unidade",
        email="usuario_unidade@test.com",
        is_active=True,
    )
    usuario.set_password(pwd)
    usuario.save()
    usuario.unidades.add(escola_sp)

    return usuario

@pytest.mark.django_db
class TestInativarUnidadeService:
    """Testes do service InativarUnidadeService."""

    def test_nao_permite_inativar_unidade_rede_diferente_indireta(
        self, escola_sp, user_gipe_admin
    ):
        escola_sp.rede = "DIRETA"
        escola_sp.ativa = True
        escola_sp.save()

        service = InativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
        )

        with pytest.raises(ValidationError) as exc:
            service.executar()

        assert exc.value.message == "Somente unidades da rede indireta podem ser inativadas."

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is True

    def test_inativa_unidade_rede_indireta(
        self, escola_sp, user_gipe_admin
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = True
        escola_sp.save()

        service = InativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
        )

        service.executar()

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is False

    def test_chama_inativar_usuario_service_para_cada_usuario(
        self, escola_sp, user_gipe_admin, usuario_vinculado_unidade
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = True
        escola_sp.save()

        service = InativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
        )

        with patch(
            "apps.users.services.gestao_usuario_service.InativarUsuarioService.inativar"
        ) as mock_inativar:
            service.executar()

        mock_inativar.assert_called_once_with(
            usuario_vinculado_unidade,
            str(user_gipe_admin),
        )

    def test_rollback_se_falhar_inativacao_de_usuario(
        self, escola_sp, user_gipe_admin, usuario_vinculado_unidade
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = True
        escola_sp.save()

        service = InativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
        )

        with patch(
            "apps.users.services.gestao_usuario_service.InativarUsuarioService.inativar",
            side_effect=ValidationError("Erro ao inativar usuário"),
        ):
            with pytest.raises(ValidationError):
                service.executar()

        escola_sp.refresh_from_db()
        usuario_vinculado_unidade.refresh_from_db()

        assert escola_sp.ativa is True
        assert usuario_vinculado_unidade.is_active is True