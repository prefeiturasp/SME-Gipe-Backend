from django.utils import timezone
from django.db import transaction

class InativarUsuarioService:

    @staticmethod
    def inativar(usuario_a_ser_inativado, usuario_responsavel, motivo_inativacao, flag_via_unidade):

        if not usuario_a_ser_inativado.is_active:
            return usuario_a_ser_inativado

        with transaction.atomic():
            usuario_a_ser_inativado.is_active = False
            usuario_a_ser_inativado.data_inativacao = timezone.now()
            usuario_a_ser_inativado.responsavel_inativacao = usuario_responsavel
            usuario_a_ser_inativado.motivo_inativacao = motivo_inativacao
            usuario_a_ser_inativado.inativado_via_unidade = flag_via_unidade

            usuario_a_ser_inativado.save(
                update_fields=[
                    "is_active",
                    "data_inativacao",
                    "responsavel_inativacao",
                    "motivo_inativacao",
                    "inativado_via_unidade",
                ]
            )

        return usuario_a_ser_inativado


class ReativarUsuarioService:

    @staticmethod
    def reativar(usuario_a_ser_reativado):

        if usuario_a_ser_reativado.is_active:
            return usuario_a_ser_reativado

        with transaction.atomic():
            usuario_a_ser_reativado.is_active = True
            usuario_a_ser_reativado.data_inativacao = None
            usuario_a_ser_reativado.responsavel_inativacao = None
            usuario_a_ser_reativado.motivo_inativacao = ""
            usuario_a_ser_reativado.inativado_via_unidade = False

            usuario_a_ser_reativado.save(
                update_fields=[
                    "is_active",
                    "data_inativacao",
                    "responsavel_inativacao",
                    "motivo_inativacao",
                    "inativado_via_unidade",
                ]
            )

        return usuario_a_ser_reativado