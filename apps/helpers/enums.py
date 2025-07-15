from enum import Enum

class Cargo(Enum):
    DIRETOR_ESCOLA = 3360
    ASSISTENTE_DIRECAO = 3085

    def __str__(self):
        nomes = {
            self.DIRETOR_ESCOLA: "Diretor de escola",
            self.ASSISTENTE_DIRECAO: "Assistente de Direção"
        }
        return nomes[self]