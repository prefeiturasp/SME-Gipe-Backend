import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class IntercorrenciasService:
    """
    Service para comunicação com o microserviço de intercorrências
    """
    
    BASE_URL = settings.INTERCORRENCIAS_API_URL
    INTERNAL_TOKEN = getattr(settings, 'INTERNAL_SERVICE_TOKEN', None)
    TIMEOUT = 30  # segundos
    
    @classmethod
    def deletar_intercorrencias_usuario_inativo(cls, username: str) -> dict:
        """
        Solicita ao microserviço de intercorrências que delete as intercorrências
        em preenchimento de um usuário inativado.
        
        Args:
            username: Username do usuário inativado
            
        Returns:
            dict com resultado da operação
        """
        url = f"{cls.BASE_URL}/diretor/deletar-por-usuario-inativo/"
        
        headers = {
            'Content-Type': 'application/json',
            'X-Internal-Service-Token': cls.INTERNAL_TOKEN
        }
        
        payload = {
            'username': username
        }
        
        try:
            logger.info(f"Solicitando exclusão de intercorrências do usuário: {username}")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=cls.TIMEOUT
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(
                f"Intercorrências deletadas com sucesso. "
                f"Total: {data.get('intercorrencias_deletadas', 0)}"
            )
            
            return {
                'success': True,
                'data': data,
                'error': None,
                'error_type': None
            }
        
        except requests.exceptions.Timeout:
            error_msg = (
                f"Timeout ao comunicar com o serviço de intercorrências. "
                f"O serviço demorou mais de {cls.TIMEOUT} segundos para responder."
            )
            logger.error(error_msg)
            
            return {
                'success': False,
                'data': None,
                'error': error_msg,
                'error_type': 'TIMEOUT'
            }
            
        except requests.exceptions.ConnectionError as e:
            error_msg = (
                "Falha ao conectar com o serviço de intercorrências. Verifique se o serviço está disponível"
            )
            logger.error(f"{error_msg} - Detalhes: {str(e)}")
            
            return {
                'success': False,
                'data': None,
                'error': error_msg,
                'error_type': 'CONNECTION_ERROR'
            }
            
        except requests.exceptions.HTTPError as e:
            # Erro HTTP (4xx ou 5xx)
            status_code = e.response.status_code
            
            try:
                error_data = e.response.json()
                error_detail = error_data.get('detail', str(e))
            except Exception.HTTPError:
                error_detail = str(e)
            
            error_msg = (
                f"Erro HTTP {status_code} ao deletar intercorrências. "
                f"Detalhes: {error_detail}"
            )
            logger.error(error_msg)
            
            return {
                'success': False,
                'data': None,
                'error': error_msg,
                'error_type': f'HTTP_{status_code}'
            }
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição ao serviço de intercorrências: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'data': None,
                'error': error_msg,
                'error_type': 'REQUEST_ERROR'
            }
        
        except Exception as e:
            error_msg = f"Erro inesperado ao comunicar com serviço de intercorrências: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                'success': False,
                'data': None,
                'error': error_msg,
                'error_type': 'UNEXPECTED_ERROR'
            }