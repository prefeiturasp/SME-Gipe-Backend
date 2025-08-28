from rest_framework import serializers
from apps.users.api.serializers.validation_serializers.cpf_validate_serializer import validate_cpf

class UsuarioCoreSSOSerializer(serializers.Serializer):
    login = serializers.CharField(validators=[validate_cpf])
    nome = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)