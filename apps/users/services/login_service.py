import logging
import environ
import requests
from django.utils import timezone

from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.helpers.exceptions import AuthenticationError, InternalError, UserNotFoundError, SmeIntegracaoException


env = environ.Env()
logger = logging.getLogger(__name__)

class AutenticacaoService:
    """Serviço para autenticação de usuários no CoreSSO"""

    DEFAULT_HEADERS = {
        "accept": "application/json",
        "x-api-eol-key": env("SME_INTEGRACAO_TOKEN", default=""),
        "Content-Type": "application/json-patch+json"
    }
    DEFAULT_TIMEOUT = 10
    
    @classmethod
    def autentica(cls, login: str, senha: str) -> dict:
        """ Autentica usuário no sistema CoreSSO """

        payload = {"usuario": login, "senha": senha, "codigoSistema": env('CODIGO_SISTEMA_GIPE', default='')}
        url = f"{env('SME_INTEGRACAO_URL', default='')}/v1/autenticacao/externa"
        
        try:
            logger.info("Autenticando usuário no CoreSSO. Login: %s", login)
            
            response = requests.post(
                url,
                headers=cls.DEFAULT_HEADERS,
                timeout=cls.DEFAULT_TIMEOUT,
                json=payload
            )
            
            if response.status_code == 401:
                logger.warning("Credenciais inválidas (login: %s)", login)
                raise AuthenticationError("Credenciais inválidas")
            
            if response.status_code != 200:
                logger.warning("Erro HTTP %s ao autenticar usuário %s", response.status_code, login)
                raise SmeIntegracaoException(f"Erro ao autenticar no CoreSSO: {response.status_code}")
            
            response_data = response.json()
            
            logger.info("Usuário autenticado com sucesso: %s", login)
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error("Erro de comunicação com CoreSSO: %s", str(e))
            raise SmeIntegracaoException(f"Erro de comunicação: {str(e)}")
        
        except (AuthenticationError, SmeIntegracaoException):
            raise

        except Exception as e:
            logger.error("Erro inesperado na autenticação: %s", str(e))
            raise InternalError(f"Erro interno: {str(e)}")