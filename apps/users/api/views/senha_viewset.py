import environ
import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.users.api.serializers.senha_serializer import EsqueciMinhaSenhaSerializer, RedefinirSenhaSerializer, AtualizarSenhaSerializer
from apps.helpers.utils import is_cpf, anonimizar_email
from apps.helpers.exceptions import EmailNaoCadastrado, SmeIntegracaoException, UserNotFoundError
from apps.users.services.senha_service import SenhaService
from apps.users.services.sme_integracao_service import SmeIntegracaoService
from apps.users.services.envia_email_service import EnviaEmailService
from apps.users.services.cargos_service import CargosService

logger = logging.getLogger(__name__)
User = get_user_model()
env = environ.Env()


class EsqueciMinhaSenhaViewSet(APIView):
    permission_classes = [AllowAny]
    MENSAGEM_DRE = "E-mail não encontrado! <br/>\
Para resolver este problema, entre em contato com o Gabinete da Diretoria Regional de Educação (DRE)."
    MENSAGEM_GIPE = "E-mail não encontrado! <br/>\
Para resolver este problema, entre em contato com o GIPE."


    def post(self, request):
        serializer = EsqueciMinhaSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]

        try:
            logger.info(
                "Iniciando fluxo de esqueci minha senha. Username: %s | Tipo: %s",
                username, "CPF" if is_cpf(username) else "RF"
            )

            user_local = User.objects.filter(username=username).first()
            if not user_local:
                logger.warning("Usuário %s não encontrado no banco local.", username)
                raise UserNotFoundError("Usuário ou RF não encontrado", usuario=username)

            # Tenta buscar no CoreSSO
            try:
                result = SmeIntegracaoService.informacao_usuario_sgp(username)
                logger.info("Usuário encontrado no CoreSSO: %s", username)
            except SmeIntegracaoException:
                result = None
                logger.warning("Usuário não encontrado no CoreSSO: %s", username)

            email = result.get("email") if result else None

            # Se tiver email válido e existir na base → gera token e envia
            if email:
                logger.info(
                    "Usuário %s possui email. Iniciando envio de redefinição.", username
                )
                return self._processar_envio_email(username, email)  # Apenas executa

            # Segrega fluxo
            if is_cpf(username):
                return self._processar_fluxo_cpf(username, result, email, user_local)
            else:
                return self._processar_fluxo_rf(username, result, email, user_local)

        except EmailNaoCadastrado as e:
            logger.warning("Email não cadastrado para usuário: %s", username)
            return Response(
                { "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except UserNotFoundError as e:
            logger.warning("Usuário não autorizado ou não encontrado: %s", username)
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED      
            )

        except Exception:
            logger.exception(
                "Erro inesperado no fluxo de esqueci minha senha para username: %s", username
            )
            return Response(
                {"detail": "Ocorreu um erro ao processar sua solicitação."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _processar_envio_email(self, username, email):
        """Gera token e envia email de reset."""
        logger.info("Gerando token de reset para usuário: %s", username)
        token_data = SenhaService.gerar_token_para_reset(username, email)

        link_reset = f"{env('FRONTEND_URL')}/recuperar-senha/{token_data['uid']}/{token_data['token']}"
        contexto_email = {
            "nome_usuario": token_data.get("name"),
            "link_reset": link_reset,
            "aplicacao_url": env("FRONTEND_URL"),
        }

        EnviaEmailService.enviar(
            destinatario=email,
            assunto="Redefinição de senha",
            template_html="emails/reset_senha.html",
            contexto=contexto_email,
        )

        logger.info("Email de redefinição enviado com sucesso para usuário: %s", username)
        return Response(
                    {
                        "detail": f"Seu link de recuperação de senha foi enviado para {anonimizar_email(email)}. <br/>\
Verifique sua caixa de entrada ou lixo eletrônico!",
                    },
                    status=status.HTTP_200_OK,
                )

    def _processar_fluxo_rf(self, username, result, email, user_local):
        """Processa fluxo para RF (7-8 dígitos)."""
        logger.info("Processando fluxo RF para usuário: %s", username)

        if not result:
            logger.warning("RF %s não encontrado no CoreSSO", username)
            raise UserNotFoundError("Usuário ou RF não encontrado")

        if not email:
            logger.info("RF %s sem email cadastrado. Verificando cargos...", username)
            cargos_data = CargosService.get_cargos(username, result.get("nome", ""))
            cargo_permitido = CargosService.get_cargo_permitido(cargos_data)

            if cargo_permitido:  # Diretor ou Assistente
                logger.warning("RF %s é Diretor/Assistente sem email cadastrado.", username)
                raise EmailNaoCadastrado(self.MENSAGEM_DRE)

            # Verifica no banco local
            if getattr(user_local, "cargo_id", None) in [0, 1]:
                logger.warning("RF %s sem email cadastrado. Encontrado no banco com cargo GIPE.", username)
                raise EmailNaoCadastrado(self.MENSAGEM_GIPE)


        logger.warning("RF %s sem cargo válido para acesso ao GIPE.", username)
        raise UserNotFoundError(
            f"Olá {result.get('nome', '').split(" ")[0]}! Desculpe, mas o acesso ao GIPE é restrito a perfis específicos."
        )


    def _processar_fluxo_cpf(self, username, result, email, user_local):
        """Processa fluxo para CPF (11 dígitos)."""
        logger.info("Processando fluxo CPF para usuário: %s", username)

        if result:  # Achou no CoreSSO
            logger.info("CPF %s encontrado no CoreSSO. Verificando cargos...", username)

            if user_local.cargo_id == 3360 and not email:
                logger.warning("CPF %s é Diretor sem email cadastrado.", username)
                raise EmailNaoCadastrado(self.MENSAGEM_DRE)


        else:  # Não achou no CoreSSO → verificar banco
            logger.warning("CPF %s não encontrado no CoreSSO. Consultando banco local.", username)

            if user_local.rede == "INDIRETA" and user_local.is_validado and user_local.email:
                logger.info("CPF %s encontrado na rede indireta.", username)
                return self._processar_envio_email(username, user_local.email)

            if not getattr(user_local, "email", None):
                logger.warning("CPF %s encontrado no banco sem email cadastrado.", username)
                raise EmailNaoCadastrado(self.MENSAGEM_DRE)


            logger.error("CPF %s não atende nenhum fluxo válido.", username)
            raise UserNotFoundError("Usuário ou RF não encontrado", usuario=username)

        # Se nenhum caso específico for levantado, considera fluxo não tratado
        logger.error("Fluxo CPF não tratado para usuário: %s", username)
        raise UserNotFoundError(
                    f"Olá {result.get('nome', '').split(" ")[0]}! Desculpe, mas o acesso ao GIPE é restrito a perfis específicos."
                )    



class RedefinirSenhaViewSet(APIView):
    """
    ViewSet para redefinição de senha usando UID.
    
    Endpoints:
    - POST /users/password/reset/ - Redefine a senha do usuário usando UID
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Redefine a senha do usuário após validar token e dados.
        
        Fluxo:
        1. Valida dados do request (uid, token, senhas)
        2. Decodifica UID e busca usuário
        3. Tenta redefinir senha no serviço externo (SME)
        4. Se sucesso, atualiza senha local no Django
        5. Retorna resposta apropriada
        """
        
        serializer = RedefinirSenhaSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.warning("Dados inválidos na redefinição de senha: %s", str(e))
            return Response(
                {
                    "status": "error", 
                    "detail": "Dados inválidos.", 
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pega o usuário validado do serializer (mais seguro)
        user = serializer.validated_data["user"]
        new_password = serializer.validated_data["password"]

        logger.info("Iniciando redefinição de senha para usuário ID: %s", user.id)

        try:
            with transaction.atomic():
                # 1. Tenta redefinir a senha no serviço externo primeiro
                SmeIntegracaoService.redefine_senha(user.username, new_password)
                
                # 2. Se a integração for bem-sucedida, atualiza a senha no Django
                user.set_password(new_password)
                user.save(update_fields=["password"])
                
                # 3. Log de sucesso (sem dados sensíveis)
                logger.info("Senha redefinida com sucesso para usuário ID: %s", user.id)
                
                return Response(
                    {
                        "status": "success", 
                        "detail": "Senha redefinida com sucesso."
                    }, 
                    status=status.HTTP_200_OK
                )
                
        except SmeIntegracaoException as e:
            logger.error("Erro na integração SME para usuário ID %s: %s", user.id, str(e))
            return Response(
                {
                    "status": "error", 
                    "detail": str(e)
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.exception("Erro inesperado na redefinição de senha para usuário ID: %s", user.id)
            return Response(
                {
                    "status": "error",
                    "detail": "Erro interno do servidor. Tente novamente mais tarde.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AtualizarSenhaViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AtualizarSenhaSerializer(data=request.data, context={"request": request})

        if not serializer.is_valid():
            logger.warning(f"Erro de validação: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        user = request.user
        nova_senha = serializer.validated_data["nova_senha"]

        try:
            with transaction.atomic():
                SmeIntegracaoService.redefine_senha(user.username, nova_senha)

                user.set_password(nova_senha)
                user.save(update_fields=["password"])

                logger.info("Usuário ID %s alterou a senha com sucesso.", user.id)

                return Response(
                    {"detail": "Senha alterada com sucesso."},
                    status=status.HTTP_200_OK,
                )

        except SmeIntegracaoException as e:
            logger.error("Erro na integração SME para alteração de senha do usuário ID %s: %s", user.id, str(e))
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.exception("Erro inesperado na alteração de senha do usuário ID: %s", user.id)
            return Response(
                {"detail": "Erro interno do servidor."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
