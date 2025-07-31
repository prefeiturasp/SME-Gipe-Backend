import logging
import environ
import requests
from datetime import datetime

from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.helpers.exceptions import AuthenticationError, InternalError, UserNotFoundError

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
        
    @classmethod
    def _authenticate_user_by_cpf(cls, cpf: str, senha: str) -> dict:
        """
        Autentica o usuário utilizando o CPF diretamente do banco de dados.
        """

        try:
            usuario = User.objects.get(cpf=cpf)

            if not usuario.check_password(senha):
                logger.warning("Senha incorreta para o CPF informado: %s", cpf)
                raise AuthenticationError("Senha inválida.")
            
            if usuario.rede != "INDIRETA":
                logger.warning("Usuário com CPF %s não pertence à rede INDIRETA ou PARCEIRA", cpf)
                raise UserNotFoundError("Acesso restrito a usuários da rede INDIRETA ou PARCEIRA.", usuario=usuario.name)

            logger.info("Usuário autenticado com sucesso via CPF: %s", cpf)

            usuario.last_login = datetime.now()
            usuario.save()

            token = RefreshToken.for_user(usuario)

            return {
                "name": usuario.name,
                "email": usuario.email,
                "cpf": usuario.cpf,
                "login": usuario.username,
                "visoes": [],
                "perfil_acesso": {
                    "codigo": usuario.cargo.codigo,
                    "nome": usuario.cargo.nome
                },
                "unidade_lotacao": [
                    {"codigo": u["codigo_eol"], "nomeUnidade": u["nome"]}
                    for u in usuario.unidades.all().values("codigo_eol", "nome")
                ] if usuario.unidades.exists() else [],
                "token": str(token.access_token)
            }

        except User.DoesNotExist:
            logger.warning("Usuário com CPF %s não encontrado", cpf)
            raise AuthenticationError("Usuário não encontrado.")
        
        except AuthenticationError:
            raise

        except UserNotFoundError:
            raise 

        except Exception as e:
            logger.error("Erro interno na autenticação via CPF: %s", str(e))
            raise InternalError("Erro interno ao autenticar via CPF.")