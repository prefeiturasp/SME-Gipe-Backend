from rest_framework import serializers


def validate_cpf(cpf: str) -> str:
    """
    Valida se o CPF é válido:
    - Deve ter 11 dígitos
    - Não pode ser uma sequência repetida
    - Deve passar pelo cálculo dos dígitos verificadores
    """

    cpf = ''.join(filter(str.isdigit, str(cpf)))

    if len(cpf) != 11:
        raise serializers.ValidationError("CPF deve conter exatamente 11 dígitos.")

    if cpf == cpf[0] * 11:
        raise serializers.ValidationError("CPF inválido: todos os dígitos iguais.")

    # Validação dos dígitos verificadores
    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
        digito = ((soma * 10) % 11) % 10
        if digito != int(cpf[i]):
            raise serializers.ValidationError("CPF inválido.")

    return cpf