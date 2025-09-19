import logging
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError, DatabaseError

from apps.users.models import Cargo
from apps.users.services.cargos_service import CargosService
from apps.users.services.login_service import AutenticacaoService
from apps.users.api.serializers.login_serializer import LoginSerializer
from apps.helpers.exceptions import AuthenticationError, UserNotFoundError

User = get_user_model()
logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    """View para autenticação de usuários"""

    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):
        """ Endpoint para autenticação de usuário """

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
        
        try:
            auth_data = self._authenticate_user(login, senha)
            cargo_autorizado = self._valida_cargo_permitido(login, auth_data)
            user_data = self._build_user_response(login, senha, auth_data, cargo_autorizado)
            
            logger.info("Autenticação realizada com sucesso para usuário: %s", login)
            return Response(data=user_data, status=status.HTTP_200_OK)
            
        except AuthenticationError as e:
            logger.warning("Falha na autenticação: %s", str(e))
            return Response(
                {'detail': 'Usuário e/ou senha inválida'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except UserNotFoundError as e:
            logger.warning("Usuário sem perfil de acesso autorizado: %s", login)
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

    def _valida_cargo_permitido(self, rf: str, auth_data: dict) -> dict:
        """ Valida se o usuário possui um cargo autorizado para acesso ao sistema. """

        # Busca cargo permitido
        cargo_permitido = CargosService.get_cargo_permitido(auth_data)

        if not cargo_permitido:
            if cargo_alternativo := self._get_cargo_gipe_ou_ponto_focal(rf):
                logger.info("Usuário com RF %s tem cargo GIPE ou PONTO FOCAL DRE", rf)
                return cargo_alternativo
            
            perfis = auth_data.get('perfis')
            if perfis and (perfil_autorizado := self._get_cargo_guide_indireta_parceira(perfis)):
                logger.info("Usuário %s tem o perfil de Diretor de escola", rf)
                return perfil_autorizado
            
            logger.info("Cargo não permitido.")
            raise UserNotFoundError("Acesso restrito a perfis específicos", usuario=auth_data.get('nome', 'Usuário').split(' ')[0])

        return cargo_permitido
    
    def _get_cargo_guide_indireta_parceira(self, perfis: list) -> dict | None:
        """ Valida se o usuário tem perfil CoreSSO de Diretor de Escola """
        return CargosService.get_cargo_perfil_guide(perfis)
        
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

    def create_or_update_user_with_cargo(self, login: str, senha: str, auth_data: dict, cargo_autorizado: dict) -> dict:
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
                    username=login,
                    defaults={
                        'name': auth_data['nome'],
                        'cpf': auth_data['numeroDocumento'],
                        'email': auth_data['email'],
                        'cargo': cargo
                    }
                )

                user.set_password(senha)
                user.is_validado = True
                user.is_core_sso = True
                user.last_login = timezone.now()
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
    
    def _build_user_response(self, login: str, senha: str, auth_data: dict, cargo_autorizado: dict) -> dict:
        """Monta resposta com dados do usuário"""
            
        _user = self.create_or_update_user_with_cargo(login, senha, auth_data, cargo_autorizado)

        # Gera tokens JWT
        tokens = self._generate_token(_user)
        return {
            "name": auth_data.get('nome', ''),
            "email": auth_data.get('email', ''),
            "cpf": auth_data.get('numeroDocumento', ''),
            "login": login,
            "perfil_acesso": {
                "codigo": _user.cargo.codigo,
                "nome": _user.cargo.nome
            },
            "unidade_lotacao": [
                    {"codigo": u["codigo_eol"], "nomeUnidade": u["nome"]}
                    for u in _user.unidades.all().values("codigo_eol", "nome")
                ] if _user.unidades.exists() else [],
            "token": tokens['access']
        }