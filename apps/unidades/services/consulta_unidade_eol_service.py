import logging
import environ
import requests

from apps.helpers.exceptions import InternalError, SmeIntegracaoException

env = environ.Env()
logger = logging.getLogger(__name__)


class ConsultaDadosEolService:
    """Serviço para consulta de dados da escola via SME Integração"""

    DEFAULT_HEADERS = {
        "accept": "application/json",
        "x-api-eol-key": env("SME_INTEGRACAO_TOKEN", default=""),
        "Content-Type": "application/json"
    }

    DEFAULT_TIMEOUT = 30

    @classmethod
    def consultar_dados_unidade(cls, codigo_escola_eol: str) -> dict:
        """Consulta dados da escola pelo código EOL"""

        base_url = env("SME_INTEGRACAO_URL", default="")
        url = f"{base_url}/escolas/dados/{codigo_escola_eol}"

        try:
            logger.info(
                "Consultando dados da escola no SME Integração. Código EOL: %s",
                codigo_escola_eol
            )

            response = requests.get(
                url,
                headers=cls.DEFAULT_HEADERS,
                timeout=cls.DEFAULT_TIMEOUT,
            )

            if response.status_code != 200:
                logger.warning(
                    "Erro HTTP %s ao consultar escola %s",
                    response.status_code,
                    codigo_escola_eol
                )
                raise SmeIntegracaoException(
                    f"Erro ao consultar dados da escola: {response.status_code}"
                )

            response_data = response.json()

            campos_chave = ["codigo", "nome", "codigoDRE"]
            if not any(response_data.get(campo) not in (None, 0) for campo in campos_chave):
                logger.warning(
                    "Payload vazio retornado. Escola não encontrada. Código EOL: %s",
                    codigo_escola_eol
                )
                raise SmeIntegracaoException("Por favor, verifique se o código está correto e tente novamente.")

            logger.info(
                "Dados da escola consultados com sucesso. Código EOL: %s",
                codigo_escola_eol
            )

            return response_data
        
        except SmeIntegracaoException:
            raise

        except Exception as e:
            logger.error(
                "Erro inesperado ao consultar dados da escola %s: %s",
                codigo_escola_eol,
                str(e),
            )
            raise InternalError(f"Erro interno: {str(e)}")