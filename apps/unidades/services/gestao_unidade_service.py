from django.db import transaction
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.users.services.gestao_usuario_service import InativarUsuarioService


class InativarUnidadeService:

    def __init__(self, *, unidade, usuario_responsavel):
        self.unidade = unidade
        self.usuario_responsavel = usuario_responsavel

    def executar(self):
        self._validar_rede()
        usuarios = self._obter_usuarios_da_unidade()

        with transaction.atomic():
            self._inativar_unidade()
            self._inativar_usuarios(usuarios)

    def _validar_rede(self):
        if self.unidade.rede != "INDIRETA":
            raise ValidationError(
                message="Somente unidades da rede indireta podem ser inativadas."
            )

    def _obter_usuarios_da_unidade(self):
        return User.objects.filter(
            unidades=self.unidade
        )

    def _inativar_unidade(self):
        self.unidade.ativa = False
        self.unidade.save(update_fields=["ativa"])

    def _inativar_usuarios(self, usuarios):
        for usuario in usuarios:
            InativarUsuarioService.inativar(
                usuario,
                self.usuario_responsavel
            )