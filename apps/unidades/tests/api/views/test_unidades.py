import pytest
import uuid as uuid_lib

from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices, TipoGestaoChoices

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario(dre, ue_indireta):
    user = User.objects.create_user(
        username="testeuser",
        password="senha123",
        cpf="12345678901",
        name="Usuário Teste"
    )
    user.unidades.add(ue_indireta)
    return user


@pytest.fixture
def dre():
    return Unidade.objects.create(
        uuid=uuid_lib.uuid4(),
        codigo_eol="111111",
        nome="DRE Teste",
        sigla="DRE",
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede=TipoGestaoChoices.INDIRETA
    )


@pytest.fixture
def ue_indireta(dre):
    return Unidade.objects.create(
        uuid=uuid_lib.uuid4(),
        codigo_eol="222222",
        nome="UE Indireta",
        sigla="UE",
        tipo_unidade=TipoUnidadeChoices.CEI,
        rede=TipoGestaoChoices.INDIRETA,
        dre=dre
    )


@pytest.fixture
def ue_direta(dre):
    return Unidade.objects.create(
        uuid=uuid_lib.uuid4(),
        codigo_eol="333333",
        nome="UE Direta",
        sigla="UE",
        tipo_unidade=TipoUnidadeChoices.CEI,
        rede=TipoGestaoChoices.DIRETA,
        dre=dre
    )


@pytest.mark.django_db
class TestUnidadeViewSet:

    def test_listar_dres(self, api_client, dre):
        response = api_client.get("/api/unidades/?tipo=DRE")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["nome"] == "DRE Teste"

    def test_listar_ues_indiretas(self, api_client, dre, ue_indireta, ue_direta):
        response = api_client.get(f"/api/unidades/?tipo=UE&dre={dre.uuid}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["nome"] == "UE Indireta"

    def test_listar_ues_sem_dre(self, api_client):
        response = api_client.get("/api/unidades/?tipo=UE")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_listar_ues_com_uuid_invalido(self, api_client):
        response = api_client.get("/api/unidades/?tipo=UE&dre=uuid-invalido")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_listar_com_tipo_invalido(self, api_client):
        response = api_client.get("/api/unidades/?tipo=INVALIDO")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_listar_sem_tipo(self, api_client, dre, ue_indireta, ue_direta):
        response = api_client.get("/api/unidades/")
        assert response.status_code == status.HTTP_200_OK
        nomes = [u["nome"] for u in response.data]
        assert "DRE Teste" in nomes
        assert "UE Indireta" in nomes
        assert "UE Direta" in nomes

    def test_batch_sucesso(self, api_client, dre, ue_indireta, ue_direta):
        codigos = [dre.codigo_eol, ue_indireta.codigo_eol]
        response = api_client.post("/api/unidades/batch/", {"codigos": codigos}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert str(dre.codigo_eol) in response.data
        assert str(ue_indireta.codigo_eol) in response.data
        assert str(ue_direta.codigo_eol) not in response.data

    def test_batch_codigos_vazio(self, api_client):
        response = api_client.post("/api/unidades/batch/", {"codigos": []}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {}

    def test_batch_codigos_nao_lista(self, api_client):
        response = api_client.post("/api/unidades/batch/", {"codigos": "nao-lista"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Campo 'codigos' deve ser uma lista."