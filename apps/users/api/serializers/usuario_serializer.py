import re
import environ


from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.unidades.models.unidades import Unidade

User = get_user_model()
env = environ.Env()
BASE_CORESSO_AUTH = env("BASE_CORESSO_AUTH")


class UserCreateSerializer(serializers.ModelSerializer):

    unidades = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=Unidade.objects.all(),
        many=True
    )
    cpf = serializers.CharField()
    username = serializers.CharField(validators=[])
    email = serializers.EmailField(validators=[])

    class Meta:
        model = User
        fields = [
            'username', 
            'name', 'email', 'cpf',
            'cargo', 'unidades', 'rede'
        ]

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=False)
        if not valid:
            first_field, first_error = next(iter(self.errors.items()))
            message = first_error[0] if isinstance(first_error, list) else str(first_error)

            self._errors = {
                "detail": message,
                "field": first_field
            }

            if raise_exception:
                raise serializers.ValidationError(self._errors)

        return valid

    def validate_cpf(self, value):

        cpf = re.sub(r'\D', '', value)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            raise serializers.ValidationError("CPF inválido.")
        
        if User.objects.filter(cpf=cpf).exists():
            raise serializers.ValidationError("Já existe uma conta com este CPF.")
        
        return cpf

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Já existe uma conta com este CPF.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")

        if not value.endswith("@sme.prefeitura.sp.gov.br"):
            raise serializers.ValidationError("Utilize seu e-mail institucional.")

        return value

    def create(self, validated_data):

        unidades = validated_data.pop('unidades', [])
        validated_data['is_validado'] = False

        username = validated_data.get("username")
        senha_padrao = f"{BASE_CORESSO_AUTH}{username[-4:]}"
        
        user = User.objects.create_user(password=senha_padrao, **validated_data)
        user.unidades.set(unidades)
        
        return user
    

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name"]
        extra_kwargs = {
            "name": {
                "required": True,
                "allow_blank": False,
                "error_messages": {
                    "blank": "Digite o seu nome completo.",
                },
            }
        }

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=False)
        if not valid:
            first_field, first_error = next(iter(self.errors.items()))
            message = first_error[0] if isinstance(first_error, list) else str(first_error)

            self._errors = {
                "detail": message,
                "field": first_field
            }

            if raise_exception:
                raise serializers.ValidationError(self._errors)

        return valid

    def validate_name(self, value):
        value = re.sub(r"\s+", " ", value.strip())

        if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$", value):
            raise serializers.ValidationError(
                "O nome deve conter apenas letras e espaços."
            )

        if len(value.split(" ")) < 2:
            raise serializers.ValidationError("Digite seu nome completo (nome e sobrenome).")

        return value