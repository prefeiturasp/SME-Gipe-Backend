import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from django.contrib.auth import get_user_model

from apps.users.api.serializers.registrar_usuario_serializer import UserCreateSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


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
        serializer.save()