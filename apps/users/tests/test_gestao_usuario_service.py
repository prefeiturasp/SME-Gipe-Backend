import pytest
from unittest.mock import patch
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.users.services.gestao_usuario_service import (
    InativarUsuarioService,
    ReativarUsuarioService,
)
from apps.helpers.exceptions import IntercorrenciasDeletionError
from apps.users.models import Cargo

User = get_user_model()


@pytest.mark.django_db
class TestInativarUsuarioService:
    """Testes para o service InativarUsuarioService."""

    def test_inativar_usuario_ja_inativo_nao_altera_dados(self):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")
        data_inativacao = timezone.now()

        usuario = User.objects.create(
            username="usuario_inativo",
            cpf="01234567891",
            name="Usuário Inativo",
            cargo=cargo,
            is_active=False,
            data_inativacao=data_inativacao,
            responsavel_inativacao="01234567899",
        )

        resultado = InativarUsuarioService.inativar(
            usuario_a_ser_inativado=usuario,
            usuario_responsavel="NOVO_ADMIN",
            motivo_inativacao="Teste",
            flag_via_unidade=False
        )

        usuario.refresh_from_db()

        assert resultado == usuario
        assert usuario.is_active is False
        assert usuario.data_inativacao.replace(microsecond=0) == data_inativacao.replace(microsecond=0)
        assert usuario.responsavel_inativacao == "01234567899"
        assert usuario.motivo_inativacao == ""
        assert usuario.inativado_via_unidade == False

    @patch(
        "apps.users.services.gestao_usuario_service.IntercorrenciasService.deletar_intercorrencias_usuario_inativo",
        return_value={"success": True, "data": {"intercorrencias_deletadas": 0}, "error": None},
    )
    def test_inativar_usuario_nao_altera_outros_campos(self, _mock_deletar):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")
        usuario = User.objects.create(
            username="usuario_original",
            cpf="55566677788",
            name="Usuário Original",
            cargo=cargo,
            is_active=True,
        )

        InativarUsuarioService.inativar(
            usuario_a_ser_inativado=usuario,
            usuario_responsavel="01234567899",
            motivo_inativacao="Teste",
            flag_via_unidade=False
        )

        usuario.refresh_from_db()

        assert usuario.name == "Usuário Original"
        assert usuario.cpf == "55566677788"
        assert usuario.is_active is False
        assert usuario.data_inativacao is not None
        assert usuario.responsavel_inativacao == "01234567899"
        assert usuario.motivo_inativacao == "Teste"
        assert usuario.inativado_via_unidade is False

    @patch(
        "apps.users.services.gestao_usuario_service.IntercorrenciasService.deletar_intercorrencias_usuario_inativo",
        return_value={"success": False, "data": None, "error": "falha"},
    )
    def test_inativar_usuario_falha_intercorrencias_retorna_erro(self, _mock_deletar):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")
        usuario = User.objects.create(
            username="usuario_falha",
            cpf="12345678900",
            name="Usuario Falha",
            cargo=cargo,
            is_active=True,
        )

        with pytest.raises(IntercorrenciasDeletionError, match="falha"):
            InativarUsuarioService.inativar(
                usuario_a_ser_inativado=usuario,
                usuario_responsavel="01234567899",
                motivo_inativacao="Teste",
                flag_via_unidade=False,
            )

    @patch(
        "apps.users.services.gestao_usuario_service.IntercorrenciasService.deletar_intercorrencias_usuario_inativo",
        side_effect=Exception("boom"),
    )
    def test_inativar_usuario_erro_inesperado_intercorrencias(self, _mock_deletar):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")
        usuario = User.objects.create(
            username="usuario_erro",
            cpf="98765432100",
            name="Usuario Erro",
            cargo=cargo,
            is_active=True,
        )

        with pytest.raises(IntercorrenciasDeletionError, match="boom"):
            InativarUsuarioService.inativar(
                usuario_a_ser_inativado=usuario,
                usuario_responsavel="01234567899",
                motivo_inativacao="Teste",
                flag_via_unidade=False,
            )
        

@pytest.mark.django_db
class TestReativarUsuarioService:
    """Testes para o service ReativarUsuarioService."""

    def test_reativar_usuario_inativo_atualiza_dados_com_sucesso(self):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")

        usuario = User.objects.create(
            username="usuario_inativo",
            cpf="11122233344",
            name="Usuário Inativo",
            cargo=cargo,
            is_active=False,
            data_inativacao=timezone.now(),
            responsavel_inativacao="admin",
            motivo_inativacao="Teste",
            inativado_via_unidade=True,
        )

        resultado = ReativarUsuarioService.reativar(usuario)

        usuario.refresh_from_db()

        assert resultado == usuario
        assert usuario.is_active is True
        assert usuario.data_inativacao is None
        assert usuario.responsavel_inativacao is None
        assert usuario.motivo_inativacao == ""
        assert usuario.inativado_via_unidade is False

    def test_reativar_usuario_ja_ativo_nao_altera_dados(self):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")

        usuario = User.objects.create(
            username="usuario_ativo",
            cpf="99988877766",
            name="Usuário Ativo",
            cargo=cargo,
            is_active=True,
        )

        resultado = ReativarUsuarioService.reativar(usuario)

        usuario.refresh_from_db()

        assert resultado == usuario
        assert usuario.is_active is True
        assert usuario.data_inativacao is None
        assert usuario.responsavel_inativacao is None
