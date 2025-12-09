# apps/users/api/serializers/usuario_admin_serializer.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.unidades.models.unidades import Unidade
from apps.users.models import Cargo

User = get_user_model()

class GestaoUsuarioSerializer(serializers.ModelSerializer):
    unidades = serializers.PrimaryKeyRelatedField(
        queryset=Unidade.objects.all(),
        many=True
    )
    is_app_admin = serializers.BooleanField(required=False)
    

    class Meta:
        model = User
        fields = [
            "uuid",
            "username", 
            "name", 
            "email", 
            "cpf",
            "cargo", 
            "rede",
            "unidades",
            "is_validado",
            "is_app_admin",
            "is_core_sso",
        ]

    def validate_unidades(self, unidades):
        """
        Ponto Focal só pode atribuir unidades da própria DRE.
        GIPE pode qualquer unidade.
        Diretor não deveria estar criando usuários, mas se estiver, bloqueia.
        """
        request = self.context["request"]
        user = request.user
        
        if not user.is_app_admin:
            raise serializers.ValidationError(
                "Você não tem permissão para definir unidades de outros usuários."
        )

        if not user.is_gipe and not user.is_ponto_focal:
            raise serializers.ValidationError(
                "Você não tem permissão para definir unidades de outros usuários."
            )

        if user.is_ponto_focal:
            allowed_dres = set(
                user.unidades.values_list("codigo_eol", flat=True).distinct()
            )
            for u in unidades:
                if u.dre_id not in allowed_dres:
                    raise serializers.ValidationError(
                       "Ponto Focal só pode cadastrar usuários para unidades de sua DRE."
                    )

        return unidades

    def validate_is_app_admin(self, value):
        """
        Somente GIPE pode marcar outro usuário como admin.
        """
        request = self.context["request"]
        user = request.user
        if value and not user.is_gipe:
            raise serializers.ValidationError(
                "Somente usuários com perfil GIPE podem atribuir perfil administrador."
            )
        return value
    
    def is_valid(self, raise_exception=False):

        valid = super().is_valid(raise_exception=False)
        if not valid:
            first_field, first_error_list = next(iter(self.errors.items()))
            message = (
                first_error_list[0]
                if isinstance(first_error_list, list)
                else str(first_error_list)
            )

            if isinstance(self._errors, dict) and "detail" in self._errors:
                error_dict = self._errors
            else:
                error_dict = {"detail": f"{first_field}: {message}"}

            self._errors = error_dict

            if raise_exception:
                raise serializers.ValidationError(self._errors)

        return valid

    def create(self, validated_data):
        unidades = validated_data.pop("unidades", [])
        is_app_admin = validated_data.pop("is_app_admin", False)
        request = self.context["request"]
        user_request = request.user

        validated_data.setdefault("is_validado", True)

        # Garantir que Ponto Focal não consiga forçar is_app_admin via payload
        if not user_request.is_gipe:
            is_app_admin = False

        novo_user = User.objects.create_user(**validated_data)
        novo_user.unidades.set(unidades)
        novo_user.is_app_admin = is_app_admin
        novo_user.save(update_fields=["is_app_admin"])

        return novo_user

    def update(self, instance, validated_data):
        unidades = validated_data.pop("unidades", None)
        is_app_admin = validated_data.pop("is_app_admin", None)
        request = self.context["request"]
        user_request = request.user

        # Campos sensíveis: só GIPE pode mexer em is_app_admin
        if is_app_admin is not None:
            if user_request.is_gipe:
                instance.is_app_admin = is_app_admin
            # se não for GIPE, simplesmente ignora

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if unidades is not None:
            self.validate_unidades(unidades)  # reuso da validação
            instance.unidades.set(unidades)

        return instance
