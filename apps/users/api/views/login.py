import logging
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import ValidationError

from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError, DatabaseError

from apps.users.models import Cargo
from apps.users.services.cargos import CargosService
from apps.users.services.login import AutenticacaoService
from apps.helpers.exceptions import AuthenticationError, UserNotFoundError
from apps.users.api.serializers.validate_login import LoginSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    """View para autenticação de usuários"""

    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):
        """
        Endpoint para autenticação de usuários

        Fluxo:
        1. Valida entrada com serializer
        2. Autentica via CoreSSO (RF) ou ORM (CPF)
        3. Busca cargos
        4. Retorna dados do usuário + token
        """

        logger.info("Iniciando processo de autenticação")

        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            return Response(
                {'detail': 'Credenciais inválidas'},
                status=status.HTTP_400_BAD_REQUEST
            )

        login = serializer.validated_data["username"]
        senha = serializer.validated_data["password"]
        auth_method = serializer.validated_data["auth_method"]
        
        try:
            if auth_method == "cpf":
                user_data = self._authenticate_user_by_cpf(login, senha)

            else:
                auth_data = self._authenticate_user(login, senha)  
                usuario_name = auth_data['nome'].split(' ')[0]
                eol_data = self._get_user_cargo(login, usuario_name)
                cargo_autorizado = self._valida_cargo_permitido(login, eol_data, usuario_name)
                unidade_lotacao = self._get_unidade_lotacao(eol_data)
                user_data = self._build_user_response(senha, auth_data, cargo_autorizado, unidade_lotacao)
            
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
                {'detail': f'Olá {e.usuario}! Desculpe, mas o acesso ao GIPE é restrito a perfis específicos.'}, 
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
    
    def _authenticate_user_by_cpf(self, login: str, senha: str) -> dict:
        """Autentica usuário usando a Base Local"""
        return AutenticacaoService._authenticate_user_by_cpf(login, senha)
    
    def _get_user_cargo(self, rf: str, usuario_name: str) -> dict:
        """Busca e valida cargo do usuário"""
        return CargosService.get_cargos(rf, usuario_name)

    def _valida_cargo_permitido(self, rf: int, eol_data: dict, usuario_name: str) -> dict:
        """Valida se o usuário possui um cargo autorizado para acesso ao sistema."""

        # Busca cargo permitido
        cargo_permitido = CargosService.get_cargo_permitido(eol_data)

        if not cargo_permitido:
            if cargo_alternativo := self._get_cargo_gipe_ou_ponto_focal(rf):
                logger.info("Usuário com RF %s tem cargo GIPE ou PONTO FOCAL DRE", rf)
                return cargo_alternativo
            
            cargos_disponiveis = eol_data.get('cargos', [])
            logger.info("Cargo não permitido. Cargos disponíveis: %s", [c.get('codigo') for c in cargos_disponiveis])
            raise UserNotFoundError("Acesso restrito a perfis específicos", usuario=usuario_name)

        return cargo_permitido

    def _get_unidade_lotacao(self, eol_data: dict) -> list:
        """Retorna a unidade de lotação como lista, independentemente da estrutura recebida."""

        unidade = eol_data.get('unidadeExercicio') or eol_data.get('unidadesLotacao', [])
        if isinstance(unidade, list):
            return unidade
        return [unidade]

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

    def create_or_update_user_with_cargo(self, senha: str, auth_data: dict, cargo_autorizado: dict) -> dict:
        """
        Cria ou atualiza um cargo e um usuário associado a ele, garantindo que ambas operações 
        ocorram juntas de forma segura.
        """

        try:
            with transaction.atomic():
                # Criação/atualização do cargo
                cargo, _ = Cargo.objects.update_or_create(
                    codigo=cargo_autorizado['codigo'],
                    defaults={
                        'nome': cargo_autorizado['nome']
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
            raise IntegrityError('Erro de integridade ao salvar os dados. Verifique se já existem registros conflitantes.')

        except DatabaseError as e:
            logger.error(f'Erro geral de banco de dados: {e}')
            raise DatabaseError('Erro no banco de dados. Tente novamente mais tarde.')

        except Exception as e:
            logger.error(f'Erro inesperado: {e}')
            raise DatabaseError('Ocorreu um erro inesperado. Verifique os dados e tente novamente.')
        
    def _generate_token(self, user: dict) -> dict:
        """Gera tokens JWT para o usuário"""

        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    
    def _build_user_response(self, senha: str, auth_data: dict, cargo_autorizado: dict, unidade_lotacao: dict) -> dict:
        """Monta resposta com dados do usuário"""
            
        _user = self.create_or_update_user_with_cargo(senha, auth_data, cargo_autorizado)

        # Gera tokens JWT
        tokens = self._generate_token(_user)
        return {
            "name": auth_data.get('nome', ''),
            "email": auth_data.get('email', ''),
            "cpf": auth_data.get('cpf', ''),
            "login": auth_data.get('login', ''),
            "visoes": auth_data.get('visoes', []),
            "perfil_acesso": {
                "codigo": _user.cargo.codigo,
                "nome": _user.cargo.nome
            },
            "unidade_lotacao": unidade_lotacao,
            "token": tokens['access']
        }