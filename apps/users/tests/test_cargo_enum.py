import pytest
from apps.helpers.enums import Cargo  

def test_cargo_values():
    assert Cargo.DIRETOR_ESCOLA.value == 3360
    assert Cargo.ASSISTENTE_DIRECAO.value == 3085

def test_cargo_str():
    assert str(Cargo.DIRETOR_ESCOLA) == "Diretor de escola"
    assert str(Cargo.ASSISTENTE_DIRECAO) == "Assistente de Direção"