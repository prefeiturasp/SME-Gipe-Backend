from apps.permissions.base_admin_permission import BaseScopedAdminPermission


class CanManageUsers(BaseScopedAdminPermission):
    """
    Gestão de usuários.
    - Não-admin pode editar/ver apenas o próprio usuário.
    """

    message = "Você não possui permissão para gerenciar usuários."
    allow_self_access_for_non_admin = True

    def get_object_dres(self, obj):
        """
        Retorna as DREs das unidades associadas ao usuário alvo.
        """
        return set(
            obj.unidades
                .exclude(dre__isnull=True)
                .values_list("dre__uuid", flat=True)
        )


class CanApproveUser(BaseScopedAdminPermission):
    """
    Permissão para aprovar usuários.
    """

    message = "Você não possui permissão para aprovar usuários."
    allow_self_access_for_non_admin = False
    pf_allowed_actions = ["aprovar"]

    def get_object_dres(self, obj):
        return set(
            obj.unidades
                .exclude(dre__isnull=True)
                .values_list("dre__uuid", flat=True)
        )
