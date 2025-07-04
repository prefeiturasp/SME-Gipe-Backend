class AuthenticationError(Exception):
    """Erro de autenticação personalizado"""
    pass

class CargoNotFoundError(Exception):
    """Erro quando cargo não é encontrado"""
    pass

class UserNotFoundError(Exception):
    """Erro quando usuário não é encontrado"""
    pass