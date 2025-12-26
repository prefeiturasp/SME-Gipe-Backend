from django.utils import timezone
from django.db import transaction

class InativarUsuarioService:

    @staticmethod
    def inativar(usuario_a_ser_inativado, usuario_responsavel):

        if not usuario_a_ser_inativado.is_active:
            return usuario_a_ser_inativado

        with transaction.atomic():
            usuario_a_ser_inativado.is_active = False
            usuario_a_ser_inativado.data_inativacao = timezone.now()
            usuario_a_ser_inativado.responsavel_inativacao = usuario_responsavel

            usuario_a_ser_inativado.save(
                update_fields=[
                    "is_active",
                    "data_inativacao",
                    "responsavel_inativacao",
                ]
            )

        return usuario_a_ser_inativado