from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.users.models import User
from apps.users.services.envia_email_service import EnviaEmailService
from apps.users.services.gestao_usuario_service import InativarUsuarioService, ReativarUsuarioService
from apps.unidades.models.unidades import TipoGestaoChoices


class InativarUnidadeService:

    def __init__(self, *, unidade, usuario_responsavel, motivo_inativacao):
        self.unidade = unidade
        self.usuario_responsavel = usuario_responsavel
        self.motivo_inativacao = motivo_inativacao

    def executar(self):
        self._validar_rede()
        usuarios = self._obter_usuarios_da_unidade()

        with transaction.atomic():
            self._inativar_unidade()
            self._inativar_usuarios(usuarios)

    def _validar_rede(self):
        if self.unidade.rede != TipoGestaoChoices.INDIRETA:
            raise ValidationError({"detail": "Somente unidades da rede indireta podem ser inativadas."})

    def _obter_usuarios_da_unidade(self):
        return User.objects.filter(
            unidades=self.unidade
        )

    def _inativar_unidade(self):
        self.unidade.ativa = False
        self.unidade.data_inativacao = timezone.now()
        self.unidade.responsavel_inativacao = self.usuario_responsavel
        self.unidade.motivo_inativacao = self.motivo_inativacao
        self.unidade.save(update_fields=[
            "ativa",
            "data_inativacao",
            "responsavel_inativacao",
            "motivo_inativacao"
        ])

    def _inativar_usuarios(self, usuarios):
        for usuario in usuarios:
            if not usuario.is_active:
                continue

            InativarUsuarioService.inativar(
                usuario,
                self.usuario_responsavel,
                self.motivo_inativacao,
                True
            )

            contexto_email = {
                "nome_usuario": usuario.name,
                "motivo_inativacao": self.motivo_inativacao,
                "nome_ue": self.unidade.nome
            }

            EnviaEmailService.enviar(
                destinatario=usuario.email,
                assunto="Inativação da Unidade Educacional no GIPE",
                template_html="emails/inativacao_unidade.html",
                contexto=contexto_email,
            )


class ReativarUnidadeService:

    def __init__(self, *, unidade, usuario_responsavel, motivo_reativacao):
        self.unidade = unidade
        self.usuario_responsavel = usuario_responsavel
        self.motivo_reativacao = motivo_reativacao

    def executar(self):
        self._validar_rede()
        usuarios = self._obter_usuarios_da_unidade_para_reativar()

        with transaction.atomic():
            self._reativar_unidade()
            self._reativar_usuarios(usuarios)

    def _validar_rede(self):
        if self.unidade.rede != TipoGestaoChoices.INDIRETA:
            raise ValidationError({"detail": "Somente unidades da rede indireta podem ser reativadas."})
    
    def _obter_usuarios_da_unidade_para_reativar(self):
        return User.objects.filter(
            unidades=self.unidade,
            is_active=False,
            inativado_via_unidade=True,
        )

    def _reativar_unidade(self):
        self.unidade.ativa = True
        self.unidade.data_reativacao = timezone.now()
        self.unidade.responsavel_reativacao = self.usuario_responsavel
        self.unidade.motivo_reativacao = self.motivo_reativacao

        self.unidade.data_inativacao = None
        self.unidade.responsavel_inativacao = ""
        self.unidade.motivo_inativacao = ""

        self.unidade.save(update_fields=[
            "ativa",
            "data_reativacao",
            "responsavel_reativacao",
            "motivo_reativacao",
            "data_inativacao",
            "responsavel_inativacao",
            "motivo_inativacao",
        ])
    
    def _reativar_usuarios(self, usuarios):
        for usuario in usuarios:
            ReativarUsuarioService.reativar(
                usuario_a_ser_reativado=usuario
            )

            contexto_email = {
                "nome_usuario": usuario.name,
                "motivo_reativacao": self.motivo_reativacao,
                "nome_ue": self.unidade.nome
            }

            EnviaEmailService.enviar(
                destinatario=usuario.email,
                assunto="Reativação de perfil no GIPE",
                template_html="emails/reativacao_unidade.html",
                contexto=contexto_email,
            )