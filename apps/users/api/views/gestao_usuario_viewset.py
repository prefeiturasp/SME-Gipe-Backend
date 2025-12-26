import environ
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.users.api.serializers.gestao_usuario_serializer import GestaoUsuarioListaSerializer, GestaoUsuarioSerializer, GestaoUsuarioRetrieveSerializer
from apps.users.permissions import CanManageUsers, CanApproveUser
from apps.unidades.models.unidades import TipoUnidadeChoices, TipoGestaoChoices

from apps.users.services.envia_email_service import EnviaEmailService
from apps.users.services.usuario_core_sso_service import CriaUsuarioCoreSSOService

from uuid import UUID
from apps.users.services.gestao_usuario_service import InativarUsuarioService

User = get_user_model()
env = environ.Env()


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
    
    def get_serializer_class(self):
        
        if self.action == "list":
            return GestaoUsuarioListaSerializer
        elif self.action == "retrieve":
            return GestaoUsuarioRetrieveSerializer

        return GestaoUsuarioSerializer
    

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        qs = self.queryset


        if user.is_gipe:
            base_qs = qs

        elif user.is_ponto_focal:

            dres_pf_uuids = user.unidades.filter(
                tipo_unidade=TipoUnidadeChoices.DRE
            ).values_list("uuid", flat=True)

            base_qs = qs.filter(
                unidades__dre__uuid__in=dres_pf_uuids
            ).distinct()

        else:

            base_qs = qs.filter(uuid=user.uuid)


        dre_uuid = params.get("dre")
        if dre_uuid and user.is_gipe:
            base_qs = base_qs.filter(
                unidades__dre__uuid=dre_uuid
            ).distinct()


        unidade_uuid = params.get("unidade")
        if unidade_uuid:
            base_qs = base_qs.filter(
                unidades__uuid=unidade_uuid
            ).distinct()

        ativo_param = params.get("ativo")
        if ativo_param is not None:
            ativo_bool = str(ativo_param).lower() in ["true", "1", "t", "yes", "sim"]
            base_qs = base_qs.filter(is_active=ativo_bool)


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

        if usuario.is_validado:
            return Response(
                {"detail": "Usuário já está aprovado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dados_usuario = {
                "login": usuario.username,
                "nome": usuario.name,
                "email": usuario.email,
            }

            CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario)

        except Exception:
            return Response(
                {"detail": "Erro ao criar o usuário no Core SSO."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contexto_email = {
            "nome_usuario": usuario.name,
            "aplicacao_url": env("FRONTEND_URL"),
            "senha": env("BASE_CORESSO_AUTH"),
        }
        
        EnviaEmailService.enviar(
            destinatario=usuario.email,
            assunto="Seu acesso ao GIPE foi aprovado!",
            template_html="emails/cadastro_aprovado.html",
            contexto=contexto_email,
        )

        usuario.is_validado = True
        usuario.data_aprovacao = timezone.now()
        usuario.responsavel_aprovacao = str(request.user)

        usuario.save(
            update_fields=[
                "is_validado",
                "data_aprovacao",
                "responsavel_aprovacao"
            ]
        )

        usuario = self.get_object() # Atualiza a instancia
        serializer = self.get_serializer(usuario)

        return Response(
            {
                "detail": "Usuário aprovado com sucesso.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    
    @action(detail=True, methods=["post"], permission_classes=[CanApproveUser])
    def reprovar(self, request, uuid=None):

        usuario = self.get_object()
        justificativa = request.data.get("justificativa")

        if not justificativa:
            return Response(
                {"detail": "Justificativa é obrigatória para reprovação."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if usuario.is_validado:
            return Response(
                {"detail": "Usuário já aprovado não pode ser reprovado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contexto_email = {
            "nome_usuario": usuario.name,
            "justificativa_admin": justificativa,
        }

        EnviaEmailService.enviar(
            destinatario=usuario.email,
            assunto="Acesso ao Gabinete Integrado de Proteção Escolar (GIPE)",
            template_html="emails/cadastro_recusado.html",
            contexto=contexto_email,
        )

        usuario.delete()

        return Response(
            {"detail": "Usuário reprovado com sucesso."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["put"], permission_classes=[CanApproveUser])
    def inativar(self, request, uuid=None):

        try:
            _uuid = UUID(uuid)
        except (ValueError, TypeError):
            return Response(
                {"detail": "UUID informado é inválido."},
                status=status.HTTP_404_NOT_FOUND
            )

        usuario = User.objects.filter(uuid=_uuid).first()
        if not usuario:
            return Response(
                {"detail": "Usuário não encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        InativarUsuarioService.inativar(
            usuario_a_ser_inativado=usuario,
            usuario_responsavel=str(request.user)
        )

        return Response(
            {"detail": "Usuário inativado com sucesso."},
            status=status.HTTP_200_OK
        )