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
