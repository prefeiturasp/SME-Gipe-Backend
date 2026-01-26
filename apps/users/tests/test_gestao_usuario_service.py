import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.users.services.gestao_usuario_service import InativarUsuarioService, ReativarUsuarioService
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

    def test_inativar_usuario_nao_altera_outros_campos(self):
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