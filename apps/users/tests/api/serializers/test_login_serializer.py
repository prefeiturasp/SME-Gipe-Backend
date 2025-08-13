import pytest
from rest_framework.exceptions import ValidationError
from apps.users.api.serializers.login_serializer import LoginSerializer


@pytest.mark.parametrize("username,expected_digits,auth_method", [
    ("1234567", "1234567", "rf"),
    ("12345678", "12345678", "rf"),
    ("123.456.789-00", "12345678900", "cpf"),
    ("123.456-78", "12345678", "rf"),
])

def test_valid_usernames(username, expected_digits, auth_method):
    data = {"username": username, "password": "secret"}
    serializer = LoginSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data['username'] == expected_digits
    assert serializer.validated_data['auth_method'] == auth_method

@pytest.mark.parametrize("username", [
    "abc123",
    "1234",
    "123456789",
    "!!!",
    "",
    None,
])

def test_invalid_usernames(username):
    data = {"username": username, "password": "secret"}
    serializer = LoginSerializer(data=data)
    with pytest.raises(ValidationError) as excinfo:
        serializer.is_valid(raise_exception=True)
    assert 'username' in str(excinfo.value)

def test_missing_password():
    data = {"username": "1234567"}
    serializer = LoginSerializer(data=data)
    assert not serializer.is_valid()
    assert "password" in serializer.errors

def test_missing_username():
    data = {"password": "secret"}
    serializer = LoginSerializer(data=data)
    assert not serializer.is_valid()
    assert "username" in serializer.errors