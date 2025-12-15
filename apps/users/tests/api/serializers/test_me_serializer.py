import secrets
import pytest
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model

from apps.users.models import Cargo
from apps.unidades.models.unidades import (
    Unidade,
    TipoGestaoChoices,
    TipoUnidadeChoices,
)
from apps.users.api.serializers.me_serializer import UserMeSerializer

User = get_user_model()


@pytest.fixture
def user_factory(db):
    def _create_user(
        username="usuario",
        name="Usuário Teste",
        email="email@teste.com",
        cpf="12345678901",
        rede=TipoGestaoChoices.DIRETA,
        cargo=None,
    ):
        pwd = secrets.token_urlsafe(16)
        user = User.objects.create_user(
            username=username,
            name=name,
            email=email,
            cpf=cpf,
            rede=rede,
            cargo=cargo,
        )
        user.set_password(pwd)
        user.save()
        return user

    return _create_user


@pytest.fixture
def dre(db):
    return Unidade.objects.create(
        codigo_eol="111111",
        nome="DRE Teste",
        sigla="DRE",
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede=TipoGestaoChoices.INDIRETA,
    )


@pytest.fixture
def ue_indireta(db, dre):
    return Unidade.objects.create(
        codigo_eol="222222",
        nome="UE Indireta",
        sigla="UEI",
        tipo_unidade=TipoUnidadeChoices.CEI,
        rede=TipoGestaoChoices.INDIRETA,
        dre=dre,
    )


@pytest.fixture
def ue_direta(db, dre):
    return Unidade.objects.create(
        codigo_eol="333333",
        nome="UE Direta",
        sigla="UED",
        tipo_unidade=TipoUnidadeChoices.CEI,
        rede=TipoGestaoChoices.DIRETA,
        dre=dre,
    )


@pytest.mark.django_db
class TestUserMeSerializer:

    def test_user_com_cargo(self, user_factory):
        cargo = Cargo.objects.create(codigo=10, nome="Diretor")

        user = user_factory(
            username="usuario1",
            name="Usuário Teste",
            email="teste@email.com",
            cpf="12345678901",
            rede=TipoGestaoChoices.DIRETA,
            cargo=cargo,
        )

        data = UserMeSerializer(user).data
        assert data["perfil_acesso"] == {"codigo": 10, "nome": "Diretor"}
        assert data["unidades"] == []

    def test_user_sem_cargo_mockado(self):
        user = MagicMock()
        user.cargo = None
        user.unidades.select_related.return_value.all.return_value = []

        data = UserMeSerializer(user).data
        assert data["perfil_acesso"] is None
        assert data["unidades"] == []

    def test_user_com_unidades(self, user_factory, dre, ue_indireta, ue_direta):
        cargo = Cargo.objects.create(codigo=20, nome="Professor")

        user = user_factory(
            username="usuario3",
            name="Usuário Unidades",
            email="unidades@email.com",
            cpf="55555555555",
            rede=TipoGestaoChoices.INDIRETA,
            cargo=cargo,
        )
        user.unidades.add(ue_indireta, ue_direta)
        user.save()

        data = UserMeSerializer(user).data

        ue = next(u for u in data["unidades"] if u["ue"]["codigo_eol"] == ue_indireta.codigo_eol)
        assert ue["ue"]["nome"] == ue_indireta.nome
        assert ue["ue"]["sigla"] == ue_indireta.sigla
        assert ue["dre"]["codigo_eol"] == dre.codigo_eol
        assert ue["dre"]["nome"] == dre.nome
        assert ue["dre"]["sigla"] == dre.sigla

        ue = next(u for u in data["unidades"] if u["ue"]["codigo_eol"] == ue_direta.codigo_eol)
        assert ue["ue"]["nome"] == ue_direta.nome
        assert ue["ue"]["sigla"] == ue_direta.sigla
        assert ue["dre"]["codigo_eol"] == dre.codigo_eol
        assert ue["dre"]["nome"] == dre.nome
        assert ue["dre"]["sigla"] == dre.sigla

    def test_user_sem_unidades(self, user_factory):
        cargo = Cargo.objects.create(codigo=30, nome="Coordenador")

        user = user_factory(
            username="usuario4",
            name="Usuário Sem Unidades",
            email="sem@email.com",
            cpf="44444444444",
            rede=TipoGestaoChoices.DIRETA,
            cargo=cargo,
        )

        data = UserMeSerializer(user).data
        assert data["unidades"] == []

    def test_user_com_unidade_dre(self, user_factory, dre):
        cargo = Cargo.objects.create(codigo=40, nome="Supervisor")

        user = user_factory(
            username="usuario5",
            name="Usuário DRE",
            email="dre@email.com",
            cpf="77777777777",
            rede=TipoGestaoChoices.INDIRETA,
            cargo=cargo,
        )
        user.unidades.add(dre)
        user.save()

        data = UserMeSerializer(user).data

        assert len(data["unidades"]) == 1
        unidade_data = data["unidades"][0]

        assert unidade_data["ue"]["codigo_eol"] is None
        assert unidade_data["ue"]["nome"] is None
        assert unidade_data["ue"]["sigla"] is None

        assert unidade_data["dre"]["codigo_eol"] == dre.codigo_eol
        assert unidade_data["dre"]["nome"] == dre.nome
        assert unidade_data["dre"]["sigla"] == dre.sigla