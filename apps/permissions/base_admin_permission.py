from rest_framework.permissions import BasePermission
from apps.unidades.models.unidades import TipoUnidadeChoices


class BaseScopedAdminPermission(BasePermission):
    """
    Permissão base para gestão com escopo por DRE.
    """

    message = "Você não possui permissão para realizar esta operação."
    pf_allowed_actions = ["list", "retrieve", "create", "update", "partial_update"]
    allow_self_access_for_non_admin = False

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # não-admin
        if not getattr(user, "is_app_admin", False):
            if self.allow_self_access_for_non_admin:
                return view.action in ["retrieve", "update", "partial_update"]
            return False

        # admin funcional
        if user.is_gipe:
            return True

        if user.is_ponto_focal:
            return view.action in self.pf_allowed_actions

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        # GIPE admin: acesso total
        if user.is_app_admin and user.is_gipe:
            return True

        # PF admin: checa escopo por DRE
        if user.is_app_admin and user.is_ponto_focal:
            user_dres = set(
                user.unidades
                    .filter(tipo_unidade=TipoUnidadeChoices.DRE)
                    .values_list("uuid", flat=True)
            )

            obj_dres = self.get_object_dres(obj)
            return bool(user_dres & obj_dres)

        # fallback para não-admin
        if self.allow_self_access_for_non_admin:
            return self.is_self_object(user, obj)

        return False

    def get_object_dres(self, obj) -> set:
        """
        Deve retornar um set de UUIDs das DREs associadas ao objeto.
        Subclasses DEVEM sobrescrever.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} deve implementar get_object_dres(obj)"
        )

    def is_self_object(self, user, obj) -> bool:
        return getattr(obj, "pk", None) == user.pk
