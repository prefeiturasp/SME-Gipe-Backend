import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework_simplejwt.views import TokenObtainPairView
from apps.users.services.login import AutenticacaoService
from apps.users.services.cargos import CargosService
from apps.helpers.exceptions import AuthenticationError, UserNotFoundError

logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    """View para autenticação de usuários"""

    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):
        """
        Endpoint para autenticação de usuários
        
        Fluxo:
        1. Autentica no CoreSSO
        2. Busca cargos no EOL
        3. Valida se possui cargo permitido
        4. Retorna dados do usuário
        """

        logger.info("Iniciando processo de autenticação")
        
        # Validação de entrada
        login = request.data.get("username")
        senha = request.data.get("password")
        
        if not login or not senha:
            return Response(
                {'detail': 'Login e senha são obrigatórios'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            auth_data = self._authenticate_user(login, senha)
            cargo_data = self._get_user_cargo(auth_data['login'])
            user_data = self._build_user_response(auth_data, cargo_data)
            
            logger.info("Autenticação realizada com sucesso para usuário: %s", login)
            return Response(data=user_data, status=status.HTTP_200_OK)
            
        except AuthenticationError as e:
            logger.warning("Falha na autenticação: %s", str(e))
            return Response(
                {'detail': 'Usuário e/ou senha inválida'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except UserNotFoundError as e:
            logger.warning("Usuário não encontrado no EOL: %s", login)
            return Response(
                {'detail': f'Olá {auth_data['nome'].split(' ')[0]}! Desculpe, mas o acesso ao GIPE é restrito a perfis específicos.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except Exception as e:
            logger.error("Erro interno durante autenticação: %s", str(e))
            return Response(
                {'detail': 'Erro interno do sistema. Tente novamente mais tarde.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _authenticate_user(self, login: str, senha: str) -> dict:
        """Autentica usuário no CoreSSO"""
        return AutenticacaoService.autentica(login, senha)
    
    def _get_user_cargo(self, rf: str) -> dict:
        """Busca e valida cargo do usuário"""
        # Busca cargos no EOL
        cargos_data = CargosService.get_cargos(rf)
        
        # Busca cargo permitido
        cargo_permitido = CargosService.get_cargo_permitido(cargos_data)
        
        if not cargo_permitido:
            cargos_disponiveis = cargos_data.get('cargos', [])
            logger.info("Cargo não permitido. Cargos disponíveis: %s", 
                       [c.get('codigo') for c in cargos_disponiveis])
            raise UserNotFoundError("Acesso restrito a perfis específicos")
        
        return cargo_permitido
    
    def _build_user_response(self, auth_data: dict, cargo_data: dict) -> dict:
        """Monta resposta com dados do usuário"""
        
        return {
            "name": auth_data.get('nome', ''),
            "email": auth_data.get('email', ''),
            "cpf": auth_data.get('cpf', ''),
            "login": auth_data.get('login', ''),
            "visoes": auth_data.get('visoes', []),
            "cargo": {
                "codigo": cargo_data.get('codigo'),
                "nome": cargo_data.get('nome', '')
            },
            "token": ""  # TODO: Implementar geração de token
        }