import logging
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.users.api.serializers.senha_serializer import EsqueciMinhaSenhaSerializer
from apps.helpers.exceptions import EmailNaoCadastrado, SmeIntegracaoException
from apps.users.services.senha_service import SenhaService
from apps.users.services.sme_integracao_service import SmeIntegracaoService

logger = logging.getLogger(__name__)
User = get_user_model()


class EsqueciMinhaSenhaViewSet(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EsqueciMinhaSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]

        try:
            result = SmeIntegracaoService.informacao_usuario_sgp(username)
            email = result.get("email")

            if not email:
                raise EmailNaoCadastrado(
                    "Você não tem e-mail cadastrado e por isso a redefinição não é possível. "
                    "Você deve procurar apoio na sua Diretoria Regional de Educação."
                )

            result = SenhaService.gerar_token_para_reset(username, email)

            # TODO: Enviar e-mail aqui
            return Response(result, status=status.HTTP_200_OK)

        except EmailNaoCadastrado as e:
            return Response(
                {"status": "email_nao_cadastrado", "message": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )

        except SmeIntegracaoException as e:
            return Response(
                {"status": "error", "message": f"{str(e)}"},
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            logger.exception("Erro inesperado no fluxo de esqueci minha senha")
            return Response(
                {
                    "status": "erro_interno",
                    "message": "Ocorreu um erro ao processar sua solicitação.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
