import pytest
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model

from apps.users.models import Cargo
from apps.unidades.models.unidades import Unidade, TipoGestaoChoices, TipoUnidadeChoices
from apps.users.api.serializers.me_serializer import UnidadeMiniSerializer, UserMeSerializer

User = get_user_model()


@pytest.fixture
def dre(db):
    return Unidade.objects.create(
        codigo_eol="111111",
        nome="DRE Teste",
        sigla="DRE",
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede=TipoGestaoChoices.INDIRETA
    )

@pytest.fixture
def ue_indireta(db, dre):
    return Unidade.objects.create(
        codigo_eol="222222",
        nome="UE Indireta",
        sigla="UEI",
        tipo_unidade=TipoUnidadeChoices.CEI,
        rede=TipoGestaoChoices.INDIRETA,
        dre=dre
    )

@pytest.fixture
def ue_direta(db, dre):
    return Unidade.objects.create(
        codigo_eol="333333",
        nome="UE Direta",
        sigla="UED",
        tipo_unidade=TipoUnidadeChoices.CEI,
        rede=TipoGestaoChoices.DIRETA,
        dre=dre
    )


@pytest.mark.django_db
class TestUnidadeMiniSerializer:

    def test_serializa_unidade_com_dre(self, dre, ue_indireta):
        serializer = UnidadeMiniSerializer(ue_indireta)
        data = serializer.data

        assert data["codigo_eol"] == ue_indireta.codigo_eol
        assert data["nome"] == ue_indireta.nome
        assert data["sigla"] == ue_indireta.sigla
        assert data["dre_codigo_eol"] == dre.codigo_eol

    def test_serializa_unidade_sem_dre(self):
        unidade = Unidade.objects.create(
            codigo_eol="999999",
            nome="Unidade Sem DRE",
            sigla="USD",
            tipo_unidade=TipoUnidadeChoices.CEI,
            rede=TipoGestaoChoices.DIRETA,
        )
        serializer = UnidadeMiniSerializer(unidade)
        data = serializer.data

        assert data["codigo_eol"] == "999999"
        assert data["nome"] == "Unidade Sem DRE"
        assert data["sigla"] == "USD"
        assert data["dre_codigo_eol"] is None


@pytest.mark.django_db
class TestUserMeSerializer:

    def test_user_com_cargo(self):
        cargo = Cargo.objects.create(codigo=10, nome="Diretor")
        user = User.objects.create_user(
            username="usuario1",
            password="teste123",
            name="Usuário Teste",
            email="teste@email.com",
            cpf="12345678901",
            rede=TipoGestaoChoices.DIRETA,
            cargo=cargo
        )

        data = UserMeSerializer(user).data
        assert data["perfil_acesso"] == {"codigo": 10, "nome": "Diretor"}
        assert data["unidades"] == []

    def test_user_sem_cargo_mockado(self):
        user = MagicMock()
        user.cargo = None
        user.unidades.all.return_value.values.return_value = []

        data = UserMeSerializer(user).data
        assert data["perfil_acesso"] is None
        assert data["unidades"] == []

    def test_user_com_unidades(self, dre, ue_indireta, ue_direta):
        cargo = Cargo.objects.create(codigo=20, nome="Professor")
        user = User.objects.create_user(
            username="usuario3",
            password="teste123",
            name="Usuário Unidades",
            email="unidades@email.com",
            cpf="55555555555",
            rede=TipoGestaoChoices.INDIRETA,
            cargo=cargo
        )
        user.unidades.add(ue_indireta, ue_direta)
        user.save()

        data = UserMeSerializer(user).data
        nomes = [u["nome"] for u in data["unidades"]]
        assert "UE Indireta" in nomes
        assert "UE Direta" in nomes

    def test_user_sem_unidades(self):
        cargo = Cargo.objects.create(codigo=30, nome="Coordenador")
        user = User.objects.create_user(
            username="usuario4",
            password="teste123",
            name="Usuário Sem Unidades",
            email="sem@email.com",
            cpf="44444444444",
            rede=TipoGestaoChoices.DIRETA,
            cargo=cargo
        )

        data = UserMeSerializer(user).data
        assert data["unidades"] == []