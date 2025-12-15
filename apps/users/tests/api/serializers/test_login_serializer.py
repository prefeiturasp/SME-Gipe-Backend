import pytest
import secrets
from rest_framework.exceptions import ValidationError
from apps.users.api.serializers.login_serializer import LoginSerializer
from apps.constants import LOGIN_PASS_FIELD

DUMMY_PASS = secrets.token_urlsafe(12)

@pytest.mark.parametrize("username,expected_digits", [
    ("1234567", "1234567"),
    ("12345678", "12345678"),
    ("123.456.789-00", "12345678900"),
    ("123.456-78", "12345678"),
])
def test_valid_usernames(username, expected_digits):
    data = {"username": username, LOGIN_PASS_FIELD: DUMMY_PASS}
    serializer = LoginSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data['username'] == expected_digits
    assert serializer.validated_data['secret_pass'] == DUMMY_PASS


@pytest.mark.parametrize("username", [
    "abc123",
    "1234",
    "123456789",
    "!!!",
    "",
    None,
])
def test_invalid_usernames(username):
    data = {"username": username, LOGIN_PASS_FIELD: DUMMY_PASS}
    serializer = LoginSerializer(data=data)
    with pytest.raises(ValidationError) as excinfo:
        serializer.is_valid(raise_exception=True)
    assert 'username' in str(excinfo.value)

def test_missing_pass():
    data = {"username": "1234567"}
    serializer = LoginSerializer(data=data)
    assert not serializer.is_valid()
    assert "secret_pass" in str(serializer.errors)

def test_missing_username():
    data = {LOGIN_PASS_FIELD: DUMMY_PASS}
    serializer = LoginSerializer(data=data)
    assert not serializer.is_valid()
    assert "username" in serializer.errors