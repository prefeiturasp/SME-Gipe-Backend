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

class EmailNaoCadastrado(Exception):
    """Email não cadastrado"""
    pass

class SmeIntegracaoException(Exception):
    """Problema na integração com a SME"""
    pass

class CargaUsuarioException(Exception):
    """Erro ao cadastrar usuário no CoreSSO"""
    pass