import logging
import environ
import requests
from apps.helpers.exceptions import AuthenticationError

env = environ.Env()
logger = logging.getLogger(__name__)

class AutenticacaoService:
    """Serviço para autenticação de usuários no CoreSSO"""
    
    DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {env("AUTENTICA_CORESSO_API_TOKEN", default="")}'
    }
    DEFAULT_TIMEOUT = 10
    
    @classmethod
    def autentica(cls, login: str, senha: str) -> dict:
        """
        Autentica usuário no sistema CoreSSO
        
        Args:
            login: Login do usuário
            senha: Senha do usuário
            
        Returns:
            Dict com dados do usuário autenticado
            
        Raises:
            AuthenticationError: Quando credenciais são inválidas
        """

        payload = {'login': login, 'senha': senha}
        url = f"{env('AUTENTICA_CORESSO_API_URL', default='')}/autenticacao/"
        
        try:
            logger.info("Autenticando usuário no CoreSSO. Login: %s", login)
            
            response = requests.post(
                url,
                headers=cls.DEFAULT_HEADERS,
                timeout=cls.DEFAULT_TIMEOUT,
                json=payload
            )
            
            if response.status_code != 200:
                logger.warning("Falha na autenticação. Status: %s, Login: %s", 
                             response.status_code, login)
                raise AuthenticationError("Credenciais inválidas")
            
            response_data = response.json()
            
            if not response_data.get('login'):
                logger.warning("Resposta de autenticação sem login válido: %s", login)
                raise AuthenticationError("Resposta de autenticação inválida")
            
            logger.info("Usuário autenticado com sucesso: %s", login)
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error("Erro de comunicação com CoreSSO: %s", str(e))
            raise AuthenticationError(f"Erro de comunicação: {str(e)}")

        except Exception as e:
            logger.error("Erro inesperado na autenticação: %s", str(e))
            raise AuthenticationError(f"Erro interno: {str(e)}")