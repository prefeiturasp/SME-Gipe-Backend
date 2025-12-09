# apps/users/api/views/usuario_management_viewset.py
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import get_user_model

from apps.users.api.serializers.gestao_usuario_serializer import GestaoUsuarioSerializer
from apps.users.permissions import CanManageUsers, CanApproveUser

User = get_user_model()


class GestaoUsuarioViewSet(ModelViewSet):
    """
    Gestão de usuários via painel (NextJS).
    """
    queryset = (
        User.objects
        .select_related("cargo")
        .prefetch_related("unidades")
    )
    serializer_class = GestaoUsuarioSerializer
    permission_classes = [CanManageUsers]
    lookup_field = "uuid"
    

    def get_queryset(self):
        user = self.request.user
        
        if user.is_gipe:
            return self.queryset

        if user.is_ponto_focal:
            dres = user.unidades.values_list("codigo_eol", flat=True).distinct()
            return self.queryset.filter(unidades__dre_id__in=dres).distinct()

        return self.queryset.filter(uuid=user.uuid)

    @action(detail=True, methods=["post"], permission_classes=[CanApproveUser])
    def aprovar(self, request, uuid=None):
        usuario = self.get_object()
        usuario.is_validado = True
        usuario.save(update_fields=["is_validado"])
        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)
