from rest_framework.permissions import BasePermission
from apps.unidades.models.unidades import TipoUnidadeChoices


class CanManageUsers(BasePermission):
    """
    Permissão para listar / criar / editar / visualizar usuários.
    - GIPE admin: pode tudo.
    - Ponto Focal admin: pode somente usuários da(s) DRE(s) dele.
    - Não-admin: só pode ver/editar o próprio registro.
    """
    
    message = "Você não possui permissão para gerenciar usuários."

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        # Se for admin funcional (flag is_app_admin)
        if user.is_app_admin:
            # GIPE admin → tudo na view
            if user.is_gipe:
                return True

            # Ponto Focal admin → list/retrieve/create/update/partial_update
            if user.is_ponto_focal and view.action in [
                "list", "retrieve", "create", "update", "partial_update"
            ]:
                return True

        # Não é admin funcional (is_app_admin=False):
        # pode apenas retrieve/update/partial_update, mas só do próprio usuário (checa em has_object_permission)
        if view.action in ["retrieve", "update", "partial_update"]:
            return True

        # list / create / delete / aprovar etc → proibido para não-admin
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        # GIPE admin tem acesso total
        if user.is_app_admin and user.is_gipe:
            return True

        # Ponto Focal admin → somente usuários com unidades na(s) DRE(s) dele
        if user.is_app_admin and user.is_ponto_focal:
            user_dres = set(
                user.unidades
                    .filter(tipo_unidade=TipoUnidadeChoices.DRE)
                    .values_list("codigo_eol", flat=True)
            )
            obj_dres = set(
                obj.unidades
                    .exclude(dre__isnull=True)
                    .values_list("dre_id", flat=True)
            )
            return bool(user_dres & obj_dres)

        # Qualquer outro (não-admin ou outro perfil) → só o próprio registro
        return obj.pk == user.pk



class CanApproveUser(BasePermission):
    """
    Permissão para aprovar usuários pendentes.
    - GIPE admin: aprova qualquer um.
    - PF admin: aprova apenas da(s) DRE(s) dele.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        # precisa ser admin funcional
        if not getattr(user, "is_app_admin", False):
            return False

        # e ser GIPE ou Ponto Focal
        if user.is_gipe or user.is_ponto_focal:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        # GIPE admin aprova qualquer um
        if user.is_app_admin and user.is_gipe:
            return True

        # Ponto Focal admin aprova apenas usuários da(s) DRE(s) dele
        if user.is_app_admin and user.is_ponto_focal:
            user_dres = set(
                user.unidades
                    .filter(tipo_unidade=TipoUnidadeChoices.DRE)
                    .values_list("codigo_eol", flat=True)
            )
            obj_dres = set(
                obj.unidades
                    .exclude(dre__isnull=True)
                    .values_list("dre_id", flat=True)
            )
            return bool(user_dres & obj_dres)

        return False

