import logging
import environ
import requests
from apps.helpers.enums import Cargo
from apps.helpers.exceptions import CargoNotFoundError, UserNotFoundError

env = environ.Env()
logger = logging.getLogger(__name__)

class CargosService:
    """Serviço para busca de cargos no sistema EOL"""
    
    DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'x-api-eol-key': env('SME_INTEGRACAO_TOKEN', default='')
    }
    DEFAULT_TIMEOUT = 10
    
    @classmethod
    def get_cargos(cls, rf: str) -> list[dict]:
        """
        Busca cargos do usuário no sistema EOL
        
        Args:
            rf: RF (Registro Funcional) do usuário
            
        Returns:
            Lista de cargos do usuário
            
        Raises:
            UserNotFoundError: Quando usuário não é encontrado
        """

        url = f"{env('SME_INTEGRACAO_URL', default='')}/Intranet/CarregarPerfisPorLogin/{rf}"
        
        try:
            logger.info("Buscando cargos no EOL para RF: %s", rf)
            
            response = requests.get(
                url,
                headers=cls.DEFAULT_HEADERS,
                # timeout=cls.DEFAULT_TIMEOUT TODO: Analisar demora na resposta em Homolog
            )
            
            if response.status_code == 401:
                logger.warning("Usuário não encontrado no EOL. RF: %s", rf)
                raise UserNotFoundError("Usuário não encontrado no sistema EOL")
            
            if response.status_code != 200:
                logger.error("Erro ao buscar cargos no EOL. Status: %s, RF: %s", 
                           response.status_code, rf)
                raise Exception(f"Erro na consulta de cargos: {response.status_code}")
            
            cargos_data = response.json()
            logger.info("Cargos encontrados para RF %s: %s", rf, len(cargos_data.get('cargos', [])))
            
            return cargos_data
            
        except requests.exceptions.RequestException as e:
            logger.error("Erro de comunicação com EOL: %s", str(e))
            raise Exception(f"Erro de comunicação com sistema de cargos: {str(e)}")
        except UserNotFoundError:
            raise  # Re-raise para manter a exceção específica
        except Exception as e:
            logger.error("Erro inesperado ao buscar cargos: %s", str(e))
            raise
    
    @classmethod
    def get_cargo_permitido(cls, cargos_data: dict) -> dict | None:
        """
        Extrai cargo permitido dos dados retornados
        
        Args:
            cargos_data: Dados de cargos retornados pelo EOL
            
        Returns:
            Cargo permitido ou None se não encontrado
        """

        # Prioriza cargos sobrepostos, senão usa cargos normais
        cargos_lista = cargos_data.get('cargosSobrePosto', cargos_data.get('cargos', []))
        
        if not cargos_lista:
            logger.warning("Nenhum cargo encontrado nos dados: %s", cargos_data)
            return None
        
        # Busca cargo permitido
        cargos_permitidos = [cargo for cargo in cargos_lista 
                           if cargo.get('codigo') in (Cargo.DIRETOR_ESCOLA.value, Cargo.ASSISTENTE_DIRECAO.value)]
        
        if not cargos_permitidos:
            logger.info("Nenhum cargo permitido encontrado. Cargos disponíveis: %s", 
                       [c.get('codigo') for c in cargos_lista])
            return None
        
        return cargos_permitidos[0]  # Retorna o primeiro cargo permitido