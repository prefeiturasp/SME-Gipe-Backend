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
from apps.unidades.models.unidades import Unidade
from apps.helpers.enums import Cargo as CargoEnum
from apps.users.services.cargos_service import CargosService
from apps.users.services.login_service import AutenticacaoService
from apps.users.api.serializers.login_serializer import LoginSerializer
from apps.helpers.exceptions import AuthenticationError, UserNotFoundError, SmeIntegracaoException

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
        senha = serializer.validated_data["secret_pass"]
        
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
        
        except SmeIntegracaoException as e:
            logger.warning("Falha na autenticação: %s", str(e))
            return Response(
                {'detail': 'Parece que estamos com uma instabilidade no momento. Tente entrar novamente daqui a pouco.'}, 
                status=status.HTTP_400_BAD_REQUEST
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

        if cargo_alternativo := self._get_cargo_gipe_ou_ponto_focal(rf):
            logger.info("Usuário com RF %s tem cargo GIPE ou PONTO FOCAL DRE", rf)
            return cargo_alternativo
        
        # Busca cargo permitido
        cargo_permitido = CargosService.get_cargo_permitido(auth_data)
        if not cargo_permitido:

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
    
    def validar_ou_vincular_unidade(self, data: dict, user) -> None:
        logger.info("Iniciando validação de unidade para o usuário %s", user)

        if user.cargo.codigo not in (CargoEnum.DIRETOR_ESCOLA.value, CargoEnum.ASSISTENTE_DIRECAO.value):
            logger.info("Usuário ignorado: cargo não é elegível para vínculo automático")
            return
        
        logger.info("Usuário possui cargo elegível para vínculo automático")

        if user.unidades.exists():
            logger.info("Usuário já possui unidade vinculada. Nenhuma ação necessária.")
            return

        logger.info("Usuário não possui unidade vinculada. Buscando no CoreSSO.")

        codigo_unidade = None
        unidades_lotacao = data.get("unidadesLotacao")

        if isinstance(unidades_lotacao, list) and len(unidades_lotacao) > 0:
            unidade_core = unidades_lotacao[0]
            codigo_unidade = unidade_core.get("codigo")

        elif data.get("unidadeExercicio"):
            codigo_unidade = data["unidadeExercicio"].get("codigo")

        if not codigo_unidade:
            logger.info("Código de unidade inválido ou ausente para usuário. Vínculo não realizado.")
            return

        logger.info("Buscando unidade na base local para usuário com codigo=%s", codigo_unidade)

        unidade = Unidade.objects.filter(codigo_eol=codigo_unidade).first()
        if not unidade:
            logger.info("Unidade não encontrada na base local. Nenhum vínculo realizado para usuário.")
            return
        
        user.unidades.set([unidade])

        logger.info("Usuário vinculado à unidade com sucesso!")

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
                dict_user = {
                        'name': auth_data['nome'],
                        'cpf': auth_data['numeroDocumento'],
                        'email': auth_data['email'],
                        'cargo': cargo,
                        'is_validado': True,
                        'is_core_sso':True,
                        'last_login': timezone.now(),
                    }

                user = User.objects.filter(username=login).first()

                if user and not user.check_password(senha):
                    dict_user.update({'password': senha})

                user, _ = User.objects.update_or_create(
                    username=login,
                    defaults=dict_user
                )

                self.validar_ou_vincular_unidade(auth_data, user)

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
        
    def _generate_token(self, user) -> dict:
        """Gera tokens JWT para o usuário"""

        refresh = RefreshToken.for_user(user)

        primeira_unidade = user.unidades.first()
        codigo_unidade_eol = primeira_unidade.codigo_eol if primeira_unidade else None

        refresh["username"] = user.username
        refresh["name"] = getattr(user, "name", "") or ""
        refresh["cpf"] = getattr(user, "cpf", "") or ""
        refresh["email"] = getattr(user, "email", "") or ""
        refresh["is_app_admin"] = getattr(user, "is_app_admin", False) or False
        if getattr(user, "cargo", None):
            refresh["perfil_codigo"] = user.cargo.codigo
            refresh["perfil_nome"] = user.cargo.nome
        refresh["codigo_unidade_eol"] = codigo_unidade_eol

        access = refresh.access_token
        access["username"] = user.username
        access["name"] = getattr(user, "name", "") or ""
        access["cpf"] = getattr(user, "cpf", "") or ""
        access["email"] = getattr(user, "email", "") or ""
        access["is_app_admin"] = getattr(user, "is_app_admin", False) or False
        if getattr(user, "cargo", None):
            access["perfil_codigo"] = user.cargo.codigo
            access["perfil_nome"] = user.cargo.nome
        access["codigo_unidade_eol"] = codigo_unidade_eol

        return {
            "access": str(access),
            "refresh": str(refresh),
        }


    def _build_user_response(self, login: str, senha: str, auth_data: dict, cargo_autorizado: dict) -> dict:
        """Monta resposta com dados do usuário"""
            
        _user = self.create_or_update_user_with_cargo(login, senha, auth_data, cargo_autorizado)

        if not _user.is_active:
            logger.warning("Tentativa de login com usuário inativo: %s", login)
            raise AuthenticationError({'detail': 'Usuário e/ou senha inválida'})

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