import logging
from rest_framework import serializers
from requests import ConnectTimeout, ReadTimeout

from apps.users.models import User
from apps.users.services.sme_integracao_service import SmeIntegracaoService
from apps.helpers.exceptions import CargaUsuarioException, SmeIntegracaoException
from apps.users.api.serializers.usuario_core_sso_serializer import UsuarioCoreSSOSerializer

logger = logging.getLogger(__name__)


class CriaUsuarioCoreSSOService:
    """
    Serviço responsável por criar ou atualizar usuários no CoreSSO.
    """

    @classmethod
    def cria_usuario_core_sso(cls, dados_usuario: dict) -> None:
        """ Verifica se o usuário já existe no CoreSSO e cria se não existir. """

        try:
            login = dados_usuario.get("login")
            if user_core_sso := cls._usuario_existe(login):
                logger.info("Usuário já cadastrado no CoreSSO %s.", login)
                cls._adiciona_perfil_guide_core_sso(login=login)
                cls._adiciona_flag_core_sso(login=login)
                return user_core_sso

            dados_validados = cls._validar_dados(dados_usuario)
            cls._criar_usuario(dados_validados)

            logger.info("Usuário criado no CoreSSO %s.", dados_validados["login"])

        except (ReadTimeout, ConnectTimeout) as e:
            raise CargaUsuarioException(
                f"Erro de {type(e).__name__} ao criar/atualizar usuário {dados_usuario['login']} no CoreSSO."
            )
        
        except SmeIntegracaoException as e:
            raise CargaUsuarioException(
                f"Erro {str(e)} ao criar/atualizar usuário {dados_usuario['login']} no CoreSSO."
            )
        
        except serializers.ValidationError as e:
            mensagens = cls._formatar_erros_validacao(e.detail)
            raise CargaUsuarioException(mensagens)
        
        except Exception as e:
            logger.exception("Erro inesperado ao criar/atualizar usuário %s", dados_usuario["login"])
            raise CargaUsuarioException(f"Erro inesperado: {str(e)}")

    @classmethod
    def remover_perfil_usuario_core_sso(cls, login: str) -> None:
        """
        Remove o perfil do usuário no CoreSSO e atualiza flags locais.
        O usuário continua existindo no CoreSSO, apenas sem o perfil.
        """

        try:
            SmeIntegracaoService.remover_perfil_coresso(
                login=login,
            )

            cls._remover_flags_core_sso(login=login)

            logger.info(
                "Perfil removido no CoreSSO e flags atualizadas para usuário %s.",
                login
            )

        except (ReadTimeout, ConnectTimeout) as e:
            raise CargaUsuarioException(
                f"Erro de {type(e).__name__} ao remover perfil do usuário {login} no CoreSSO."
            )

        except SmeIntegracaoException as e:
            raise CargaUsuarioException(
                f"Erro {str(e)} ao remover perfil do usuário {login} no CoreSSO."
            )

        except Exception as e:
            logger.exception("Erro inesperado ao remover perfil do usuário %s", login)
            raise CargaUsuarioException(f"Erro inesperado: {str(e)}")
        
    @classmethod
    def _usuario_existe(cls, login: str) -> dict | None:
        """ Consulta usuário existe no CoreSSO """
        return SmeIntegracaoService.usuario_core_sso_or_none(login=login)

    @classmethod
    def _adiciona_flag_core_sso(cls, login: str) -> None:
        """ Atribui a flag is_core_sso no DB local """

        try:
            user = User.objects.get(username=login)
            user.is_core_sso = True
            user.save()
        except User.DoesNotExist:
            logger.warning("Usuário com CPF %s não encontrado", login)
            raise CargaUsuarioException(f"Usuário {login} não encontrado.")
        
    @classmethod
    def _remover_flags_core_sso(cls, login: str) -> None:
        """ Marca usuário como não validado e fora do CoreSSO no DB local. """

        try:
            user = User.objects.get(username=login)
            user.is_core_sso = False
            user.is_validado = False
            user.save(update_fields=["is_core_sso", "is_validado"])
        except User.DoesNotExist:
            logger.warning("Usuário com CPF %s não encontrado ao tentar remover", login)
            raise CargaUsuarioException(f"Usuário {login} não encontrado.")
        
    @classmethod
    def _adiciona_perfil_guide_core_sso(cls, login: str) -> None:
        """ Atribui o perfil guide diretor de escola no CoreSSO """
        SmeIntegracaoService.atribuir_perfil_coresso(login=login)

    @classmethod
    def _validar_dados(cls, dados_usuario: dict) -> dict:
        """ Valida os dados do usuário usando o Serializer """

        serializer = UsuarioCoreSSOSerializer(data=dados_usuario)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
        
    @staticmethod
    def _formatar_erros_validacao(detail) -> str:
        """ Converte os erros do serializer em uma mensagem amigável. """

        mensagens = []
        for campo, erros in detail.items():
            for erro in erros:
                mensagens.append(f"{campo.capitalize()}: {erro}")
        return "Usuário inválido. Motivo(s): " + "; ".join(mensagens)

    @classmethod
    def _criar_usuario(cls, dados_usuario: dict) -> None:
        """ Cria o usuário no CoreSSO. """

        SmeIntegracaoService.cria_usuario_core_sso(
            login=dados_usuario["login"],
            nome=dados_usuario["nome"],
            email=dados_usuario["email"]
        )

        cls._adiciona_perfil_guide_core_sso(login=dados_usuario["login"])
        cls._adiciona_flag_core_sso(login=dados_usuario["login"])