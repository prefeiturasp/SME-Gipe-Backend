import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


logger = logging.getLogger(__name__)
User = get_user_model()

class SenhaService:
    """
    Serviço para lidar com a lógica de recuperação de senha via username.
    """

    @staticmethod
    def gerar_token_para_usuario(user):
        """
        Gera token e UID para reset de senha.
        """
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        return uid, token

    @staticmethod
    def gerar_token_para_reset(username: str, email:str):
        """
        Busca usuário pelo username e retorna dados para reset de senha.
        Lança UserNotFoundError se não encontrar.
        """
        logger.info(f"Iniciando geração de token para usuário: {username}")

        user = User.objects.get(username=username)

        uid, token = SenhaService.gerar_token_para_usuario(user)

        name = user.name.split(" ")[0]

        resultado = {
            "token": token,
            "uid": uid,
            "name": name,
        }

        logger.info(f"Token de reset gerado com sucesso para {username}")
        return resultado