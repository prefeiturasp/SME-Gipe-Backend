import secrets
import pytest
import uuid as uuid_lib
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from apps.unidades.models.unidades import (
    Unidade,
    TipoUnidadeChoices,
    TipoGestaoChoices,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    def _create_user(
        username="testeuser",
        cpf="12345678901",
        name="Usuário Teste",
    ):
        pwd = secrets.token_urlsafe(16)
        user = User.objects.create_user(
            username=username,
            cpf=cpf,
            name=name,
        )
        user.set_password(pwd)
        user.save()
        return user

    return _create_user


@pytest.fixture
def usuario(user_factory, dre, ue_indireta):
    user = user_factory()
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
        rede=TipoGestaoChoices.INDIRETA,
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
        dre=dre,
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
        dre=dre,
    )


@pytest.fixture
def ue_indireta_inativa(dre):
    return Unidade.objects.create(
        uuid=uuid_lib.uuid4(),
        codigo_eol="444444",
        nome="UE Indireta Inativa",
        sigla="UE",
        tipo_unidade=TipoUnidadeChoices.CEI,
        rede=TipoGestaoChoices.INDIRETA,
        dre=dre,
        ativa=False,
    )


@pytest.fixture
def dre_inativa():
    return Unidade.objects.create(
        uuid=uuid_lib.uuid4(),
        codigo_eol="555555",
        nome="DRE Inativa",
        sigla="DRE",
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede=TipoGestaoChoices.INDIRETA,
        ativa=False,
    )


@pytest.fixture
def usuario_gipe(usuario):
    usuario.is_gipe = True
    usuario.is_ponto_focal = False
    usuario.save()
    return usuario


@pytest.fixture
def usuario_ponto_focal(usuario):
    usuario.is_gipe = False
    usuario.is_ponto_focal = True
    usuario.save()
    return usuario


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

    def test_listar_ues_rede_todas(self, api_client, dre, ue_indireta, ue_direta):
        response = api_client.get(f"/api/unidades/?tipo=UE&dre={dre.uuid}&rede=TODAS")
        assert response.status_code == status.HTTP_200_OK
        nomes = [u["nome"] for u in response.data]
        assert "UE Indireta" in nomes
        assert "UE Direta" in nomes

    def test_listar_ues_rede_direta(self, api_client, dre, ue_indireta, ue_direta):
        response = api_client.get(f"/api/unidades/?tipo=UE&dre={dre.uuid}&rede=DIRETA")
        assert response.status_code == status.HTTP_200_OK
        nomes = [u["nome"] for u in response.data]
        assert "UE Direta" in nomes
        assert "UE Indireta" not in nomes

    def test_listar_ues_rede_indireta(self, api_client, dre, ue_indireta, ue_direta):
        response = api_client.get(
            f"/api/unidades/?tipo=UE&dre={dre.uuid}&rede=INDIRETA"
        )
        assert response.status_code == status.HTTP_200_OK
        nomes = [u["nome"] for u in response.data]
        assert "UE Indireta" in nomes
        assert "UE Direta" not in nomes

    def test_listar_ues_rede_invalida(self, api_client, dre):
        response = api_client.get(
            f"/api/unidades/?tipo=UE&dre={dre.uuid}&rede=INVALIDA"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_batch_sucesso(self, api_client, dre, ue_indireta, ue_direta):
        codigos = [dre.codigo_eol, ue_indireta.codigo_eol]
        response = api_client.post(
            "/api/unidades/batch/", {"codigos": codigos}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert str(dre.codigo_eol) in response.data
        assert str(ue_indireta.codigo_eol) in response.data
        assert str(ue_direta.codigo_eol) not in response.data

    def test_batch_codigos_vazio(self, api_client):
        response = api_client.post(
            "/api/unidades/batch/", {"codigos": []}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {}

    def test_batch_codigos_nao_lista(self, api_client):
        response = api_client.post(
            "/api/unidades/batch/", {"codigos": "nao-lista"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Campo 'codigos' deve ser uma lista."
    
    def test_listar_ues_apenas_ativas(
        self, api_client, dre, ue_indireta, ue_indireta_inativa
    ):
        response = api_client.get(
            f"/api/unidades/?tipo=UE&dre={dre.uuid}&ativas=true"
        )

        assert response.status_code == status.HTTP_200_OK
        nomes = [u["nome"] for u in response.data]

        assert "UE Indireta" in nomes
        assert "UE Indireta Inativa" not in nomes
    
    def test_listar_dres_apenas_ativas(
        self, api_client, dre, dre_inativa
    ):
        response = api_client.get("/api/unidades/?tipo=DRE&ativas=true")

        assert response.status_code == status.HTTP_200_OK
        nomes = [u["nome"] for u in response.data]

        assert "DRE Teste" in nomes
        assert "DRE Inativa" not in nomes
    
    def test_listar_todas_apenas_ativas(
        self,
        api_client,
        dre,
        dre_inativa,
        ue_indireta,
        ue_indireta_inativa,
    ):
        response = api_client.get("/api/unidades/?ativas=true")

        assert response.status_code == status.HTTP_200_OK
        nomes = [u["nome"] for u in response.data]

        assert "DRE Teste" in nomes
        assert "UE Indireta" in nomes
        assert "DRE Inativa" not in nomes
        assert "UE Indireta Inativa" not in nomes
    
PATCH_PATH = (
    "apps.unidades.api.views.unidades."
    "ConsultaDadosEolService.consultar_dados_unidade"
)

@pytest.mark.django_db
class TestUnidadeViewSetConsultarEOL:

    @pytest.fixture
    def cargo_gipe(self, db):
        from apps.users.models import Cargo, User
        return Cargo.objects.create(codigo=User.PERFIL_GIPE, nome="GIPE")

    @pytest.fixture
    def cargo_ponto_focal(self, db):
        from apps.users.models import Cargo, User
        return Cargo.objects.create(
            codigo=User.PERFIL_PONTO_FOCAL, nome="Ponto Focal"
        )

    @pytest.fixture
    def usuario_gipe(self, usuario, cargo_gipe):
        usuario.cargo = cargo_gipe
        usuario.save()
        return usuario

    @pytest.fixture
    def usuario_ponto_focal(self, usuario, cargo_ponto_focal):
        usuario.cargo = cargo_ponto_focal
        usuario.save()
        return usuario

    @patch(PATCH_PATH)
    def test_consultar_eol_dre_sucesso_gipe(
        self, mock_consulta, api_client, usuario_gipe, dre
    ):
        api_client.force_authenticate(usuario_gipe)

        mock_consulta.return_value = {
            "codigo": "111111",
            "codigoDRE": "111111",
            "nomeDRE": "DRE Teste",
        }

        response = api_client.get(f"/api/unidades/{dre.pk}/consultar-eol/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["etapa_modalidade"] == "DRE"
        assert response.data["nome_unidade"] == "DRE Teste"

    @patch(PATCH_PATH)
    def test_consultar_eol_ue_sucesso(
        self, mock_consulta, api_client, usuario_gipe, ue_indireta
    ):
        api_client.force_authenticate(usuario_gipe)

        mock_consulta.return_value = {
            "codigo": "222222",
            "codigoDRE": "111111",
            "siglaTipoEscola": "CEI ",
            "nomeExibicao": "UE Indireta",
        }

        response = api_client.get(f"/api/unidades/{ue_indireta.pk}/consultar-eol/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["etapa_modalidade"] == "CEI"
        assert response.data["nome_unidade"] == "UE Indireta"

    @patch(PATCH_PATH)
    def test_consultar_eol_usuario_sem_permissao(
        self, mock_consulta, api_client, usuario, ue_indireta
    ):
        api_client.force_authenticate(usuario)

        mock_consulta.return_value = {
            "codigo": "222222",
            "codigoDRE": "111111",
        }

        response = api_client.get(f"/api/unidades/{ue_indireta.pk}/consultar-eol/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Usuário sem permissão" in response.data["detail"]

    @patch(PATCH_PATH)
    def test_ponto_focal_nao_pode_cadastrar_dre(
        self, mock_consulta, api_client, usuario_ponto_focal, dre
    ):
        api_client.force_authenticate(usuario_ponto_focal)

        mock_consulta.return_value = {
            "codigo": "111111",
            "codigoDRE": "111111",
            "nomeDRE": "DRE Teste",
        }

        response = api_client.get(f"/api/unidades/{dre.pk}/consultar-eol/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Ponto focal não pode cadastrar DRE" in response.data["detail"]

    @patch(PATCH_PATH)
    def test_ponto_focal_ue_fora_da_dre(
        self, mock_consulta, api_client, usuario_ponto_focal, ue_indireta
    ):
        api_client.force_authenticate(usuario_ponto_focal)

        mock_consulta.return_value = {
            "codigo": "222222",
            "codigoDRE": "999999",
        }

        response = api_client.get(f"/api/unidades/{ue_indireta.pk}/consultar-eol/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "A unidade não pertence à sua DRE" in response.data["detail"]

    @patch(PATCH_PATH)
    def test_consultar_eol_servico_erro(
        self, mock_consulta, api_client, usuario_gipe, ue_indireta
    ):
        api_client.force_authenticate(usuario_gipe)

        mock_consulta.side_effect = Exception("Erro no EOL")

        response = api_client.get(f"/api/unidades/{ue_indireta.pk}/consultar-eol/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Erro no EOL"