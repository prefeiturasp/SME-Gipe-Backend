from rest_framework import serializers
from django.core.validators import validate_email

from apps.users.models import User


class AlteracaoEmailSerializer(serializers.Serializer):
    new_email = serializers.CharField(
        required=True,
        error_messages={
            "blank": "O campo de e-mail é obrigatório.",
            "required": "O campo de e-mail é obrigatório.",
        }
    )

    def is_valid(self, raise_exception=False):

        valid = super().is_valid(raise_exception=False)
        if not valid:

            first_error = next(iter(self.errors.values()))
            message = first_error[0] if isinstance(first_error, list) else str(first_error)

            self._errors = {"detail": message}

            if raise_exception:
                raise serializers.ValidationError(self._errors)

        return valid

    def validate_new_email(self, value):

        usuario = self.context["request"].user
        if usuario.email == value:
            raise serializers.ValidationError("O novo e-mail não pode ser igual ao atual.")

        if not value.endswith("@sme.prefeitura.sp.gov.br"):
            raise serializers.ValidationError("Utilize seu e-mail institucional.")
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")

        try:
            validate_email(value)

        except Exception:
            raise serializers.ValidationError("Digite um e-mail válido!")

        return value