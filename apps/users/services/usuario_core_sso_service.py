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
    def cria_usuario_core_sso(cls, dados_usuario: dict):
        """ Verifica se o usuário já existe no CoreSSO e cria se não existir. """

        try:
            if user_core_sso := cls._usuario_existe(dados_usuario["login"]):
                logger.info("Usuário já cadastrado no CoreSSO %s.", dados_usuario["login"])
                cls._adiciona_flag_core_sso(login=dados_usuario["login"])
                return user_core_sso

            dados_validados = cls._validar_dados(dados_usuario)

            cls._criar_usuario(dados_validados)
            cls._adiciona_flag_core_sso(login=dados_validados["login"])

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
    def _usuario_existe(cls, login: str) -> dict | None:
        """ Consulta usuário existe no CoreSSO """
        return SmeIntegracaoService.usuario_core_sso_or_none(login=login)

    @classmethod
    def _adiciona_flag_core_sso(cls, login: str):
        """ Atribui a flag is_core_sso no DB local """

        updated = User.objects.filter(username=login).update(is_core_sso=True)
        if not updated:
            logger.warning("Usuário com CPF %s não encontrado", login)
            raise CargaUsuarioException(f"Usuário {login} não encontrado.")
        
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
        return f"Usuário inválido. Motivo(s): " + "; ".join(mensagens)

    @staticmethod
    def _criar_usuario(dados_usuario: dict):
        """ Cria o usuário no CoreSSO. """

        SmeIntegracaoService.cria_usuario_core_sso(
            login=dados_usuario["login"],
            nome=dados_usuario["nome"],
            email=dados_usuario["email"]
        )