from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class EsqueciMinhaSenhaSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, min_length=7, max_length=11)

    def validate(self, data):
        username = data.get("username", "").strip()

        if not User.objects.filter(username=username).exists():
            raise serializers.ValidationError(f"Usuário {username} não encontrado.")

        return data
