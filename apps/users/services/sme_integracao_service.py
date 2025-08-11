import environ
import logging
import requests
from rest_framework import status
from apps.helpers.exceptions import SmeIntegracaoException

env = environ.Env()
logger = logging.getLogger(__name__)


class SmeIntegracaoService:
    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
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

        except requests.RequestException as err:
            logger.exception("Erro de conexão com a API externa")
            raise requests.RequestException("Erro ao conectar-se à API externa.")
