import pytest
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator

from apps.users.api.serializers.senha_serializer import RedefinirSenhaSerializer

User = get_user_model()


class TestRedefinirSenhaSerializer:

    def test_validate_success(self, db, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {
            "uid": uid,
            "token": token,
            "password": "NovaSenha@123",
            "password2": "NovaSenha@123",
        }

        ser = RedefinirSenhaSerializer(data=data)
        assert ser.is_valid(), ser.errors

        # Verifica que o serializer injeta o `user` e remove campos supérfluos
        v = ser.validated_data
        assert "user" in v
        assert v["user"].pk == user.pk
        assert "password" in v
        assert "password2" not in v
        assert "uid" not in v

    def test_password_mismatch(self, db, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {
            "uid": uid,
            "token": token,
            "password": "NovaSenha@123",
            "password2": "OutraSenha@123",
        }

        ser = RedefinirSenhaSerializer(data=data)
        assert not ser.is_valid()
        assert "non_field_errors" in ser.errors
        assert "As senhas não conferem." in str(ser.errors)

    def test_invalid_uid(self, db, user):
        # base64 inválido
        data = {
            "uid": "!!base64_invalido!!",
            "token": "qualquer",
            "password": "NovaSenha@123",
            "password2": "NovaSenha@123",
        }
        ser = RedefinirSenhaSerializer(data=data)
        assert not ser.is_valid()
        assert "UID inválido" in str(ser.errors)

    def test_user_not_found(self, db):
        # UID de um PK que não existe
        fake_uid = urlsafe_base64_encode(force_bytes(999999))
        data = {
            "uid": fake_uid,
            "token": "qualquer",
            "password": "NovaSenha@123",
            "password2": "NovaSenha@123",
        }
        ser = RedefinirSenhaSerializer(data=data)
        assert not ser.is_valid()
        assert "Usuário não encontrado." in str(ser.errors)

    def test_invalid_token(self, db, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        data = {
            "uid": uid,
            "token": "token-invalido",
            "password": "NovaSenha@123",
            "password2": "NovaSenha@123",
        }
        ser = RedefinirSenhaSerializer(data=data)
        assert not ser.is_valid()
        assert "Token inválido ou expirado." in str(ser.errors)

    def test_uid_nao_numerico(self, db, user):
        uid = "XO"
        data = {
            "uid": uid,
            "token": "token-invalido",
            "password": "NovaSenha@123",
            "password2": "NovaSenha@123",
        }
        ser = RedefinirSenhaSerializer(data=data)
        assert not ser.is_valid()
        assert "UID inválido ou malformado." in str(ser.errors)
