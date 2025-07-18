import logging
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError, DatabaseError

from apps.users.models import Cargo
from apps.users.services.cargos import CargosService
from apps.users.services.login import AutenticacaoService
from apps.helpers.exceptions import AuthenticationError, UserNotFoundError

User = get_user_model()
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
            user_data = self._build_user_response(senha, auth_data, cargo_data)
            
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
            if cargo_alternativo := self._get_cargo_gipe_ou_ponto_focal(rf):
                logger.info("Usuário com RF %s tem cargo GIPE ou PONTO FOCAL DRE", rf)
                return cargo_alternativo
            
            cargos_disponiveis = cargos_data.get('cargos', [])
            logger.info("Cargo não permitido. Cargos disponíveis: %s", [c.get('codigo') for c in cargos_disponiveis])
            raise UserNotFoundError("Acesso restrito a perfis específicos")

        return cargo_permitido

    def _get_cargo_gipe_ou_ponto_focal(self, rf: str) -> dict | None:
        """
        Retorna o cargo se o usuário for GIPE ou PONTO FOCAL DRE, senão None
        """

        try:
            usuario = User.objects.get(username=rf)

            if usuario.cargo.codigo in [0, 1]:
                return {
                    'codigo': usuario.cargo.codigo,
                    'nome': usuario.cargo.nome
                }
            
        except User.DoesNotExist:
            logger.warning("Usuário com RF %s não encontrado no model User", rf)

        return None

    def create_or_update_user_with_cargo(self, senha: str, auth_data: dict, cargo_data: dict) -> dict:
        """
        Cria ou atualiza um cargo e um usuário associado a ele, garantindo que ambas operações 
        ocorram juntas de forma segura.
        """

        try:
            with transaction.atomic():
                # Criação/atualização do cargo
                cargo, _ = Cargo.objects.update_or_create(
                    codigo=cargo_data['codigo'],
                    defaults={
                        'nome': cargo_data['nome']
                    }
                )

                # Criação/atualização do usuário com o cargo
                user, _ = User.objects.update_or_create(
                    username=auth_data['login'],
                    defaults={
                        'name': auth_data['nome'],
                        'cpf': auth_data['cpf'],
                        'email': auth_data['email'],
                        'cargo': cargo
                    }
                )

                user.set_password(senha)
                user.save()

                return user

        except IntegrityError as e:
            logger.error(f'Erro de integridade no banco de dados: {e}')
            raise Exception('Erro de integridade ao salvar os dados. Verifique se já existem registros conflitantes.')

        except DatabaseError as e:
            logger.error(f'Erro geral de banco de dados: {e}')
            raise Exception('Erro no banco de dados. Tente novamente mais tarde.')

        except Exception as e:
            logger.error(f'Erro inesperado: {e}')
            raise Exception('Ocorreu um erro inesperado. Verifique os dados e tente novamente.')
        
    def _generate_token(self, user: dict) -> dict:
        """Gera tokens JWT para o usuário"""

        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    
    def _build_user_response(self, senha: str, auth_data: dict, cargo_data: dict) -> dict:
        """Monta resposta com dados do usuário"""
            
        _user = self.create_or_update_user_with_cargo(senha, auth_data, cargo_data)
        # Gera tokens JWT
        tokens = self._generate_token(_user)
        return {
            "name": auth_data.get('nome', ''),
            "email": auth_data.get('email', ''),
            "cpf": auth_data.get('cpf', ''),
            "login": auth_data.get('login', ''),
            "visoes": auth_data.get('visoes', []),
            "cargo": {
                "codigo": _user.cargo.codigo,
                "nome": _user.cargo.nome
            },
            "token": tokens['access']
        }