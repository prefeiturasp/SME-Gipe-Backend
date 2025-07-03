import logging

from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.services.login import AutenticacaoService
from apps.users.services.cargos import CargosService

User = get_user_model()
logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    """
    POST users/login/
    """

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):

        logger.info("Carregando a View de autenticação do usuario no CoreSSO...")

        login = request.data.get("username")
        senha = request.data.get("password")

        try:
            response = AutenticacaoService.autentica(login, senha)
            response_json = response.json()

            if response.status_code == 200 and response_json.get('login'):
                # TODO: Adicionar rotina para salvar usuario e criar o Token de acesso.

                response_cargos = CargosService.get_cargos(rf=response_json['login'])
                cargos_json = response_cargos.json()

                cargos_sobreposto = cargos_json['cargosSobrePosto'] if cargos_json.get('cargosSobrePosto') else \
                cargos_json['cargos']
                
                cargo = [x for x in cargos_sobreposto if x['codigo'] in [3085, 3360]][0]

                if not cargo:
                    return Response({'detail': 
                        f'Olá {response_json['nome'].split()[0]}! Desculpe, mas o acesso ao GIPE é restrito a perfis específicos.'
                    }, status=status.HTTP_401_UNAUTHORIZED)

                user_data = {
                    "name": response_json['nome'],
                    "email": response_json['email'],
                    "cpf": response_json['cpf'],
                    "login": response_json['login'],
                    "visoes": response_json['visoes'],
                    "cargo": cargo['nome'],
                    "token": ""
                }
                return Response(data=user_data, status=status.HTTP_200_OK)
            
            return Response({'detail': 'Usuário e/ou senha inválida'}, status=status.HTTP_401_UNAUTHORIZED)
        
        except Exception as e:
            return Response({'data': {'detail': f'ERROR - {e}'}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)