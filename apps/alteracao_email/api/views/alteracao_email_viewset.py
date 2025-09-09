from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.alteracao_email.api.serializers.alteracao_email_serializer import AlteracaoEmailSerializer
from apps.alteracao_email.services.alteracao_email_service import AlteracaoEmailService
from apps.helpers.exceptions import (
    TokenJaUtilizadoException,
    TokenExpiradoException
)


class SolicitarAlteracaoEmailViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):

        serializer = AlteracaoEmailSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            AlteracaoEmailService.solicitar(
                usuario=request.user,
                novo_email=serializer.validated_data["new_email"]
            )
            return Response(
                {"message": "E-mail de confirmação enviado com sucesso."},
                status=status.HTTP_201_CREATED
            )
        
        except Exception:
            return Response({"detail": "Erro inesperado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidarAlteracaoEmailViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def update(self, request, pk=None):

        try:
            AlteracaoEmailService.validar(pk)
            return Response({"message": "E-mail alterado com sucesso."}, status=status.HTTP_200_OK)
        
        except TokenJaUtilizadoException as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except TokenExpiradoException as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": "Erro inesperado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)