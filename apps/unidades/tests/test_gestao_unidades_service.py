import pytest
import secrets
from django.utils import timezone

from unittest.mock import patch
from rest_framework.exceptions import ValidationError

from apps.users.models import User, Cargo
from apps.unidades.models.unidades import Unidade, TipoGestaoChoices
from apps.unidades.services.gestao_unidade_service import InativarUnidadeService, ReativarUnidadeService

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
            motivo_inativacao="Teste"
        )

        with pytest.raises(ValidationError) as exc:
            service.executar()

        assert str(exc.value.detail["detail"]) == (
            "Somente unidades da rede indireta podem ser inativadas."
        )

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is True
        assert escola_sp.motivo_inativacao == ""

    def test_inativa_unidade_rede_indireta(
        self, escola_sp, user_gipe_admin
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = True
        escola_sp.save()

        service = InativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_inativacao="Teste"
        )

        service.executar()

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is False
        assert escola_sp.motivo_inativacao == "Teste"

    def test_rollback_se_falhar_inativacao_de_usuario(
        self, escola_sp, user_gipe_admin, usuario_vinculado_unidade
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = True
        escola_sp.save()

        service = InativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_inativacao="Teste",
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
    
    def test_envia_email_com_contexto_correto_para_usuario_inativado(
        self, escola_sp, user_gipe_admin, usuario_vinculado_unidade
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = True
        escola_sp.nome = "Escola Teste"
        escola_sp.save()

        service = InativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_inativacao="Motivo X",
        )

        with patch(
            "apps.users.services.gestao_usuario_service.InativarUsuarioService.inativar"
        ) as mock_inativar_usuario, patch(
            "apps.users.services.envia_email_service.EnviaEmailService.enviar"
        ) as mock_enviar_email:

            service.executar()

            mock_inativar_usuario.assert_called_once()
            mock_enviar_email.assert_called_once()

            kwargs = mock_enviar_email.call_args.kwargs

            assert kwargs["destinatario"] == usuario_vinculado_unidade.email
            assert kwargs["assunto"] == "Inativação da Unidade Educacional no GIPE"
            assert kwargs["template_html"] == "emails/inativacao_unidade.html"

            assert kwargs["contexto"] == {
                "nome_usuario": usuario_vinculado_unidade.name,
                "motivo_inativacao": "Motivo X",
                "nome_ue": "Escola Teste",
            }


@pytest.mark.django_db
class TestReativarUnidadeService:
    """Testes do service ReativarUnidadeService."""

    def test_nao_permite_reativar_unidade_rede_diferente_indireta(
        self, escola_sp, user_gipe_admin
    ):
        escola_sp.rede = "DIRETA"
        escola_sp.ativa = False
        escola_sp.save()

        service = ReativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_reativacao="Teste",
        )

        with pytest.raises(ValidationError) as exc:
            service.executar()

        assert str(exc.value.detail["detail"]) == (
            "Somente unidades da rede indireta podem ser reativadas."
        )

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is False
        assert escola_sp.motivo_reativacao in ("", None)

    def test_reativa_unidade_rede_indireta_e_limpa_campos_inativacao(
        self, escola_sp, user_gipe_admin
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = False

        escola_sp.data_inativacao = timezone.now()
        escola_sp.responsavel_inativacao = "Fulano"
        escola_sp.motivo_inativacao = "Encerramento"
        escola_sp.save()

        service = ReativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_reativacao="Reabertura",
        )

        service.executar()

        escola_sp.refresh_from_db()

        assert escola_sp.ativa is True
        assert escola_sp.motivo_reativacao == "Reabertura"
        assert escola_sp.responsavel_reativacao == str(user_gipe_admin)
        assert escola_sp.data_reativacao is not None

        assert escola_sp.data_inativacao is None
        assert escola_sp.responsavel_inativacao == ""
        assert escola_sp.motivo_inativacao == ""

    def test_data_reativacao_e_preenchida(
        self, escola_sp, user_gipe_admin
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = False
        escola_sp.save()

        service = ReativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_reativacao="Teste",
        )

        service.executar()

        escola_sp.refresh_from_db()

        assert escola_sp.data_reativacao is not None

    @patch("apps.unidades.services.gestao_unidade_service.EnviaEmailService.enviar")
    @patch("apps.unidades.services.gestao_unidade_service.ReativarUsuarioService.reativar")
    def test_reativa_usuarios_e_envia_email(
        self,
        mock_reativar_usuario,
        mock_envia_email,
        escola_sp,
        user_gipe_admin,
        django_user_model,
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = False
        escola_sp.save()

        usuario1 = django_user_model.objects.create(
            username="u1",
            email="u1@test.com",
            is_active=False,
            inativado_via_unidade=True,
            cpf=str(secrets.randbelow(10**11)).zfill(11),
            name="Usuário 1",
        )
        usuario1.unidades.add(escola_sp)

        usuario2 = django_user_model.objects.create(
            username="u2",
            email="u2@test.com",
            is_active=False,
            inativado_via_unidade=True,
            cpf=str(secrets.randbelow(10**11)).zfill(11),
            name="Usuário 2",
        )
        usuario2.unidades.add(escola_sp)

        service = ReativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_reativacao="Reabertura",
        )

        service.executar()

        assert mock_reativar_usuario.call_count == 2
        mock_reativar_usuario.assert_any_call(usuario_a_ser_reativado=usuario1)
        mock_reativar_usuario.assert_any_call(usuario_a_ser_reativado=usuario2)

        assert mock_envia_email.call_count == 2
        mock_envia_email.assert_any_call(
            destinatario="u1@test.com",
            assunto="Reativação de perfil no GIPE",
            template_html="emails/reativacao_unidade.html",
            contexto={
                "nome_usuario": "Usuário 1",
                "motivo_reativacao": "Reabertura",
                "nome_ue": escola_sp.nome,
            },
        )
    
    @patch("apps.unidades.services.gestao_unidade_service.ReativarUsuarioService.reativar")
    def test_transaction_rollback_se_falhar_reativacao_usuario(
        self,
        mock_reativar_usuario,
        escola_sp,
        user_gipe_admin,
        django_user_model,
    ):
        escola_sp.rede = "INDIRETA"
        escola_sp.ativa = False
        escola_sp.save()

        usuario = django_user_model.objects.create(
            username="u1",
            email="u1@test.com",
            is_active=False,
            inativado_via_unidade=True,
            cpf=str(secrets.randbelow(10**11)).zfill(11),
            name="Usuário 1",
        )
        usuario.unidades.add(escola_sp)

        mock_reativar_usuario.side_effect = Exception("Erro qualquer")

        service = ReativarUnidadeService(
            unidade=escola_sp,
            usuario_responsavel=str(user_gipe_admin),
            motivo_reativacao="Teste",
        )

        with pytest.raises(Exception):
            service.executar()

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is False

    @patch("apps.unidades.services.gestao_unidade_service.InativarUsuarioService.inativar")
    def test_inativar_unidade_ignora_usuario_ja_inativo(self, mock_inativar_usuario):
        unidade = Unidade.objects.create(
            nome="UE Teste",
            rede=TipoGestaoChoices.INDIRETA,
            ativa=True,
        )

        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")

        usuario_inativo = User.objects.create(
            username="inativo",
            cpf="11111111111",
            name="Usuário Inativo",
            cargo=cargo,
            is_active=False,
            email="teste@teste.com",
            data_inativacao=timezone.now(),
        )

        usuario_ativo = User.objects.create(
            username="ativo",
            cpf="22222222222",
            name="Usuário Ativo",
            cargo=cargo,
            email="teste@teste.com",
            is_active=True,
        )

        usuario_inativo.unidades.add(unidade)
        usuario_ativo.unidades.add(unidade)

        data_inativacao_inativo = usuario_inativo.data_inativacao

        def _fake_inativar(usuario_a_ser_inativado, usuario_responsavel, motivo_inativacao, flag_via_unidade):
            usuario_a_ser_inativado.is_active = False
            usuario_a_ser_inativado.data_inativacao = timezone.now()
            usuario_a_ser_inativado.responsavel_inativacao = usuario_responsavel
            usuario_a_ser_inativado.motivo_inativacao = motivo_inativacao
            usuario_a_ser_inativado.inativado_via_unidade = flag_via_unidade
            usuario_a_ser_inativado.save(update_fields=[
                "is_active",
                "data_inativacao",
                "responsavel_inativacao",
                "motivo_inativacao",
                "inativado_via_unidade",
            ])

        mock_inativar_usuario.side_effect = _fake_inativar

        service = InativarUnidadeService(
            unidade=unidade,
            usuario_responsavel="ADMIN",
            motivo_inativacao="Encerramento"
        )

        service.executar()

        usuario_inativo.refresh_from_db()
        usuario_ativo.refresh_from_db()
        unidade.refresh_from_db()

        assert mock_inativar_usuario.call_count == 1
        assert usuario_inativo.is_active is False
        assert usuario_inativo.data_inativacao == data_inativacao_inativo
        assert usuario_ativo.is_active is False
        assert usuario_ativo.data_inativacao is not None
        assert unidade.ativa is False