import environ
import logging
import requests
from rest_framework import status
from apps.helpers.exceptions import SmeIntegracaoException

env = environ.Env()
logger = logging.getLogger(__name__)


class SmeIntegracaoService:
    DEFAULT_HEADERS = {
        'accept': 'application/json',
        "x-api-eol-key": env("SME_INTEGRACAO_TOKEN", default=""),
    }
    DEFAULT_TIMEOUT = 10

    @classmethod
    def informacao_usuario_sgp(cls, username):
        logger.info(f"Consultando dados na API externa para: {username}")
        try:
            url = f"{env('SME_INTEGRACAO_URL', default='')}/AutenticacaoSgp/{username}/dados"  
            response = requests.get(url, headers=cls.DEFAULT_HEADERS, timeout=10)

            if response.status_code == status.HTTP_200_OK:
                return response.json()

            else:
                logger.info(f"Dados não encontrados: {response}")
                raise SmeIntegracaoException('Dados não encontrados.')

        except requests.RequestException:
            logger.exception("Erro de conexão com a API externa")
            raise requests.RequestException("Erro ao conectar-se à API externa.")
        

    @classmethod
    def redefine_senha(cls, registro_funcional, senha):
        """
        Redefine a senha de um usuário no sistema SME.
        
        IMPORTANTE: Se a nova senha for uma das senhas padrões, a API do SME 
        não permite a atualização. Para resetar para senha padrão, use o endpoint ReiniciarSenha.
        
        Args:
            registro_funcional: Username/registro funcional do usuário
            senha: Nova senha
            
        Returns:
            Dict[str, Any]: Resposta da API ou confirmação de sucesso
            
        Raises:
            SmeIntegracaoException: Em caso de erro na operação
        """

        if not registro_funcional or not senha:
            raise SmeIntegracaoException("Registro funcional e senha são obrigatórios")
        
        logger.info(
            "Iniciando redefinição de senha no CoreSSO para usuário: %s", 
            registro_funcional
        )
        
        data = {
            'Usuario': registro_funcional,
            'Senha': senha
        }

        try:

            url = f"{env('SME_INTEGRACAO_URL', default='')}/AutenticacaoSgp/AlterarSenha"  

            response = requests.post(url, data=data, headers=cls.DEFAULT_HEADERS)

            if response.status_code == status.HTTP_200_OK:
                result = "OK"
                return result
            else:
                texto = response.content.decode('utf-8')
                mensagem = texto.strip("{}'\"")
                logger.info("Erro ao redefinir senha: %s", mensagem)
                raise SmeIntegracaoException(mensagem)
        except Exception as err:
            raise SmeIntegracaoException(str(err))
        
    @classmethod
    def usuario_core_sso_or_none(cls, login: str):
        """ Consulta usuário no CoreSSO. """

        logger.info("Consultando informação do usuário %s no CoreSSO.", login)

        url = f"{env('SME_INTEGRACAO_URL', default='')}/AutenticacaoSgp/{login}/dados"

        try:
            response = requests.get(url, headers=cls.DEFAULT_HEADERS, timeout=cls.DEFAULT_TIMEOUT)

            if response.status_code == status.HTTP_200_OK:
                return response.json()

            logger.warning(
                "Usuário %s não encontrado no CoreSSO. Status: %s. Detalhes: %s",
                login,
                response.status_code,
                response.text,
            )
            return None

        except requests.RequestException as err:
            logger.error(
                "Falha de comunicação ao procurar usuário %s no CoreSSO: %s",
                login,
                str(err),
            )
            raise SmeIntegracaoException(
                f"Erro ao procurar usuário {login} no CoreSSO."
            ) from err
        
    @classmethod
    def cria_usuario_core_sso(cls, login: str, nome: str, email: str) -> bool:
        """ Cria um novo usuário no CoreSSO. """

        logger.info("Iniciando criação de usuário no CoreSSO: %s", login)

        url = f"{env('SME_INTEGRACAO_URL', default='')}/v1/usuarios/coresso"

        headers = {**cls.DEFAULT_HEADERS, "Content-Type": "application/json-patch+json"}

        payload = {
            "nome": nome,
            "documento": login,
            "codigoRf": "",
            "email": email
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=cls.DEFAULT_TIMEOUT)
            response.raise_for_status()

            logger.info("Usuário %s criado com sucesso no CoreSSO.", login)
            return True

        except requests.RequestException as err:
            logger.error(
                "Erro ao criar usuário no CoreSSO (%s). Status: %s. Detalhes: %s",
                login,
                getattr(err.response, "status_code", "N/A"),
                getattr(err.response, "text", str(err)),
            )
            raise SmeIntegracaoException(
                f"Erro ao criar o usuário {nome} no CoreSSO."
            ) from err
        
    @classmethod
    def altera_email(cls, registro_funcional, email):
        """
        Altera o email de um usuário no sistema SME.
        
        Args:
            registro_funcional: Username/registro funcional do usuário
            email: Novo Email
            
        Returns:
            Dict[str, Any]: Resposta da API ou confirmação de sucesso
            
        Raises:
            SmeIntegracaoException: Em caso de erro na operação
        """

        if not registro_funcional or not email:
            raise SmeIntegracaoException("Registro funcional e email são obrigatórios")
        
        logger.info(
            "Iniciando alteração de email no CoreSSO para usuário: %s", 
            registro_funcional
        )
        
        data = {
            'Usuario': registro_funcional,
            'Email': email
        }

        try:

            url = f"{env('SME_INTEGRACAO_URL', default='')}/AutenticacaoSgp/AlterarEmail"

            response = requests.post(url, data=data, headers=cls.DEFAULT_HEADERS)

            if response.status_code == status.HTTP_200_OK:
                result = "OK"
                return result
            else:
                texto = response.content.decode('utf-8')
                mensagem = texto.strip("{}'\"")
                logger.info("Erro ao Alterar email: %s", mensagem)
                raise SmeIntegracaoException(mensagem)
        except Exception as err:
            raise SmeIntegracaoException(str(err))
        
    @classmethod
    def atribuir_perfil_coresso(cls, login: str) -> None:
        """ Atribui o perfil guide ao usuário no CoreSSO. """

        logger.info("Iniciando atribuição de perfil guide para o login: %s", login)

        perfil_guide = env('PERFIL_INDIRETA_DIRETOR_DE_ESCOLA_GIPE', default='')
        url = f"{env('SME_INTEGRACAO_URL', default='')}/perfis/servidores/{login}/perfil/{perfil_guide}/atribuirPerfil"

        try:
            response = requests.get(url, headers=cls.DEFAULT_HEADERS, timeout=cls.DEFAULT_TIMEOUT)

            if response.status_code == status.HTTP_200_OK:
                logger.info("Perfil atribuído com sucesso ao login: %s", login)
                return

            logger.error("Falha na atribuição de perfil para %s. Status: %s, Resposta: %s", login, response.status_code, response.text)
            raise SmeIntegracaoException("Falha ao fazer atribuição de perfil.")

        except Exception as err:
            logger.exception("Erro inesperado ao atribuir perfil para %s: %s", login, err)
            raise SmeIntegracaoException(str(err))