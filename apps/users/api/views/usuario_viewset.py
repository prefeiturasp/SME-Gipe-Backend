import logging
import environ


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from django.contrib.auth import get_user_model
from django.utils.timezone import now

from apps.users.api.serializers.usuario_serializer import UserCreateSerializer
from apps.users.services.envia_email_service import EnviaEmailService

User = get_user_model()
logger = logging.getLogger(__name__)
env = environ.Env()


class UserCreateView(APIView):
    """ View para criação de novos usuários. """
    
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserCreateSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        logger.info("Requisição para criação de usuário recebida")
        serializer = self.get_serializer(data=request.data)

        try:
            if not serializer.is_valid():
                logger.warning(f"Erro de validação: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            self.perform_create(serializer)
            username = serializer.validated_data.get('username', 'usuário')
            logger.info(f"Usuário criado com sucesso: {username}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("Erro inesperado ao criar usuário")
            return Response(
                {"detail": "Erro interno ao criar usuário.", "detalhes": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """Cria o usuário e envia o e-mail de confirmação/boas-vindas."""
        user = serializer.save()
        name = user.name.split(" ")[0]

        contexto_email = {
            "nome_usuario": name,
            "aplicacao_url": env("FRONTEND_URL"),
        }

        try:
            EnviaEmailService.enviar(
                destinatario=user.email,
                assunto="Solicitação de acesso ao GIPE.",
                template_html="emails/solicitacao_cadastro.html",
                contexto=contexto_email
            )
        except Exception as e:
            logger.error(f"Falha ao enviar e-mail de confirmação: {e}")

        return user