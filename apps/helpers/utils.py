import re

def is_cpf(username: str) -> bool:
    """
    Remove pontos e traços e verifica se o username é CPF.
    Retorna True se tiver 11 dígitos, False caso contrário.
    """
    clean_username = re.sub(r'\D', '', username)  # remove tudo que não é número
    return len(clean_username) == 11


def anonimizar_email(email: str) -> str:
    """
    Anonimiza o nome de usuário de um e-mail.
    Exemplo:
        - "joaosilva@email.com" -> "joa****@email.com"
        - "ab@dominio.com" -> "a*@dominio.com"
    """
    nome_usuario, dominio = email.split('@', 1)

    if len(nome_usuario) > 3:
        nome_anonimizado = nome_usuario[:3] + '*' * (len(nome_usuario) - 3)
    else:
        nome_anonimizado = nome_usuario[0] + '*' * (len(nome_usuario) - 1)

    return f"{nome_anonimizado}@{dominio}"
