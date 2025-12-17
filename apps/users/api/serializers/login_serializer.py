import re
from rest_framework import serializers

from apps.constants import LOGIN_PASS_FIELD


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    secret_pass = serializers.CharField(write_only=True)
     
    def to_internal_value(self, data):
        if LOGIN_PASS_FIELD in data:
            data = data.copy()
            data['secret_pass'] = data.pop(LOGIN_PASS_FIELD)
        return super().to_internal_value(data)

    def validate(self, attrs):
        username = attrs.get("username")
        digits = re.sub(r'\D', '', username or '')

        if not digits.isdigit() or len(digits) not in (7, 8, 11):
            raise serializers.ValidationError({
                'username': "Login inválido. Use RF (7/8 dígitos) ou CPF (11 dígitos numéricos)."
            })

        attrs['username'] = digits
        return attrs