import pytest
from rest_framework import serializers
from apps.users.api.serializers.validation_serializers.cpf_validate_serializer import validate_cpf

@pytest.mark.parametrize("cpf_input, expected_exception, expected_msg", [
    ("1234567890", serializers.ValidationError, "CPF deve conter exatamente 11 dígitos."),
    ("11111111111", serializers.ValidationError, "CPF inválido: todos os dígitos iguais."),
    ("12345678901", serializers.ValidationError, "CPF inválido."),
])

def test_validate_cpf_erros(cpf_input, expected_exception, expected_msg):
    with pytest.raises(expected_exception) as exc:
        validate_cpf(cpf_input)
    assert expected_msg in str(exc.value)

def test_validate_cpf_valido():
    cpf_valido = "11144477735"
    result = validate_cpf(cpf_valido)
    assert result == cpf_valido