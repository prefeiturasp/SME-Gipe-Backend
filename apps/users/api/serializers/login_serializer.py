from rest_framework import serializers
import re

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        digits = re.sub(r'\D', '', username or '')

        if not digits.isdigit() or len(digits) not in (7, 8, 11):
            raise serializers.ValidationError({
                'username': "Login inválido. Use RF (7/8 dígitos) ou CPF (11 dígitos numéricos)."
            })

        attrs['username'] = digits
        return attrs