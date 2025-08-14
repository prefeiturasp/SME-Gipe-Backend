import re

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.unidades.models.unidades import Unidade

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):

    unidades = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=Unidade.objects.all(),
        many=True
    )
    cpf = serializers.CharField()

    class Meta:
        model = User
        fields = [
            'username', 'password', 'name', 'email', 'cpf',
            'cargo', 'unidades', 'rede'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_cpf(self, value):

        cpf = re.sub(r'\D', '', value)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            raise serializers.ValidationError("CPF inválido.")
        
        if User.objects.filter(cpf=cpf).exists():
            raise serializers.ValidationError("Já existe um usuário com este CPF.")
        
        return cpf

    def create(self, validated_data):

        unidades = validated_data.pop('unidades', [])
        validated_data['is_validado'] = False
        user = User.objects.create_user(**validated_data)
        user.unidades.set(unidades)
        
        return user