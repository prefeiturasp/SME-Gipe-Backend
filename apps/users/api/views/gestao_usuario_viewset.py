# apps/users/api/views/gestao_usuario_viewset.py

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import get_user_model

from apps.users.api.serializers.gestao_usuario_serializer import GestaoUsuarioListaSerializer, GestaoUsuarioSerializer
from apps.users.permissions import CanManageUsers, CanApproveUser
from apps.unidades.models.unidades import TipoUnidadeChoices, TipoGestaoChoices

User = get_user_model()


class GestaoUsuarioViewSet(ModelViewSet):
    """
    Gestão de usuários via painel (NextJS).
    """
    queryset = (
        User.objects
        .select_related("cargo")
        .prefetch_related("unidades")   # importante para otimizar filtros por DRE
    )
    serializer_class = GestaoUsuarioSerializer
    permission_classes = [CanManageUsers]
    lookup_field = "uuid"
    
    def get_serializer_class(self):
        # Para a lista (tabela), usamos o serializer "enxuto" e formatado
        if self.action == "list":
            return GestaoUsuarioListaSerializer
        # Para retrieve/create/update usamos o serializer completo de gestão
        return GestaoUsuarioSerializer
    

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        qs = self.queryset

        # ========================================================
        # 1) ESCOPO BASE: GIPE → todos, PF → somente da(s) própria(s) DRE(s)
        # ========================================================

        if user.is_gipe:
            base_qs = qs

        elif user.is_ponto_focal:
            # PF deve ver apenas usuários cujas unidades estejam na(s) DRE(s) dele
            dres_pf_uuids = user.unidades.filter(
                tipo_unidade=TipoUnidadeChoices.DRE
            ).values_list("uuid", flat=True)

            base_qs = qs.filter(
                unidades__dre__uuid__in=dres_pf_uuids
            ).distinct()

        else:
            # Outros usuários → somente eles mesmos
            base_qs = qs.filter(uuid=user.uuid)

        # ========================================================
        # 2) FILTROS VIA QUERY PARAMS
        # ========================================================

        # ----- 2.1 Filtro por DRE (APENAS GIPE) -----
        dre_uuid = params.get("dre")
        if dre_uuid and user.is_gipe:
            base_qs = base_qs.filter(
                unidades__dre__uuid=dre_uuid
            ).distinct()

        # ----- 2.2 Filtro por Unidade -----
        unidade_uuid = params.get("unidade")
        if unidade_uuid:
            base_qs = base_qs.filter(
                unidades__uuid=unidade_uuid
            ).distinct()

        # ----- 2.3 Filtro por ativo/inativo -----
        ativo_param = params.get("ativo")
        if ativo_param is not None:
            ativo_bool = str(ativo_param).lower() in ["true", "1", "t", "yes", "sim"]
            base_qs = base_qs.filter(is_active=ativo_bool)

        # ----- 2.4 Filtro por pendente de aprovação -----
        pendente = params.get("pendente_aprovacao")
        if pendente and str(pendente).lower() in ["true", "1", "t", "yes", "sim"]:
            
            base_qs = base_qs.filter(
                rede=TipoGestaoChoices.INDIRETA, 
                is_validado=False
            )

        return base_qs

    @action(detail=True, methods=["post"], permission_classes=[CanApproveUser])
    def aprovar(self, request, uuid=None):
        usuario = self.get_object()
        usuario.is_validado = True
        usuario.save(update_fields=["is_validado"])
        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)
