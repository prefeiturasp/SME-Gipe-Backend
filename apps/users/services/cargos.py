import logging

import environ
import requests

env = environ.Env()
SME_INTEGRACAO_TOKEN = env('SME_INTEGRACAO_TOKEN', default='')
SME_INTEGRACAO_URL = env('SME_INTEGRACAO_URL', default='')

logger = logging.getLogger(__name__)


class CargosService:
    DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'x-api-eol-key': SME_INTEGRACAO_TOKEN
    }
    DEFAULT_TIMEOUT = 10

    @classmethod
    def get_cargos(cls, rf):

        try:
            logger.info("Buscando os cargos para o RF: %s", rf)
            response = requests.get(
                f"{SME_INTEGRACAO_URL}/Intranet/CarregarPerfisPorLogin/{rf}",
                headers=cls.DEFAULT_HEADERS,
                # timeout=cls.DEFAULT_TIMEOUT
            )
            return response
        except Exception as e:
            logger.info("ERROR - %s", str(e))
            raise e