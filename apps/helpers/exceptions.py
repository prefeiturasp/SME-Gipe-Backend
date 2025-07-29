class AuthenticationError(Exception):
    """Erro de autenticação personalizado"""
    pass

class CargoNotFoundError(Exception):
    """Erro quando cargo não é encontrado"""
    pass

class UserNotFoundError(Exception):
    """Erro quando usuário não é encontrado"""
    def __init__(self, message, usuario=None):
        super().__init__(message)
        self.usuario = usuario

class InternalError(Exception):
    """Erro interno do sistema"""
    pass