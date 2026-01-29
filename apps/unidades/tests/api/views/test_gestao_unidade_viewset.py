import pytest
import secrets
import uuid as uuid_lib

from unittest.mock import patch, Mock
from django.urls import reverse
from rest_framework import status

from apps.users.models import Cargo, User
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices, TipoGestaoChoices


@pytest.mark.django_db
class TestGestaoUnidadeViewSetPermissoes:
    """Testes de permissões e queryset para GestaoUnidadeViewSet."""

    def test_gipe_admin_visualiza_todas_unidades(
        self, api_client, user_gipe_admin, dre_sp, dre_outra, escola_sp, escola_outra
    ):
        """GIPE admin deve visualizar todas as unidades."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 4
        uuids = [str(u["uuid"]) for u in response.data]
        assert str(dre_sp.uuid) in uuids
        assert str(dre_outra.uuid) in uuids
        assert str(escola_sp.uuid) in uuids
        assert str(escola_outra.uuid) in uuids

    def test_ponto_focal_visualiza_apenas_sua_dre_e_escolas(
        self, api_client, user_pf_admin, dre_sp, dre_outra, escola_sp, escola_outra
    ):
        """Ponto Focal deve visualizar apenas unidades da sua DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Deve ver apenas escola_sp (que pertence à dre_sp) e a dre_sp
        assert len(response.data) == 2
        uuids = [str(u["uuid"]) for u in response.data]
        assert str(dre_sp.uuid) in uuids
        assert str(escola_sp.uuid) in uuids
        # Não deve ver dre_outra nem escola_outra
        assert str(dre_outra.uuid) not in uuids
        assert str(escola_outra.uuid) not in uuids

    def test_usuario_comum_nao_visualiza_nenhuma_unidade(
        self, api_client, user_comum, dre_sp, escola_sp
    ):
        """Usuário comum não deve visualizar nenhuma unidade."""
        api_client.force_authenticate(user=user_comum)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_usuario_nao_autenticado_nao_acessa(self, api_client):
        """Usuário não autenticado não deve acessar."""
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestGestaoUnidadeViewSetList:
    """Testes para listagem de unidades."""

    def test_list_retorna_serializer_lista(
        self, api_client, user_gipe_admin, dre_sp, escola_sp
    ):
        """Listagem deve usar GestaoUnidadeListaSerializer."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verifica campos do serializer de lista
        assert "tipo_unidade_label" in response.data[0]
        assert "rede_label" in response.data[0]
        assert "dre_nome" in response.data[0]
        assert "dre_uuid" in response.data[0]

    def test_list_filtra_por_dre(
        self, api_client, user_gipe_admin, dre_sp, escola_sp, escola_outra
    ):
        """Aplica filtro por DRE retornando apenas unidades vinculadas a ela."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url, {"dre": str(dre_sp.uuid)})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["dre_uuid"] == str(dre_sp.uuid)
        assert response.data[0]["uuid"] == str(escola_sp.uuid)
        uuids = {item["uuid"] for item in response.data}
        assert str(escola_outra.uuid) not in uuids

    def test_list_filtra_por_rede(
        self, api_client, user_gipe_admin, dre_sp, escola_sp
    ):
        """Filtra unidades por rede."""
        Unidade.objects.create(
            codigo_eol="400000",
            nome="EMEF Parceira",
            tipo_unidade=TipoUnidadeChoices.EMEF,
            rede="INDIRETA",
            dre=dre_sp,
        )

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url, {"rede": "INDIRETA"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["rede"] == "INDIRETA"
        assert response.data[0]["nome"] == "EMEF Parceira"

    def test_list_filtra_por_tipo_unidade(
        self, api_client, user_gipe_admin, dre_sp, dre_outra, escola_sp
    ):
        """Filtra unidades por tipo."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url, {"tipo_unidade": TipoUnidadeChoices.DRE})

        assert response.status_code == status.HTTP_200_OK
        retornados = {item["uuid"] for item in response.data}
        assert retornados == {str(dre_sp.uuid), str(dre_outra.uuid)}
        assert all(
            item["tipo_unidade"] == TipoUnidadeChoices.DRE for item in response.data
        )

    def test_list_filtra_por_ativa_false(
        self, api_client, user_gipe_admin, escola_sp, escola_outra
    ):
        """Filtra unidades ativas/inativas considerando strings truthy/falsy."""
        escola_sp.ativa = False
        escola_sp.save()

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        response = api_client.get(url, {"ativa": "false"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["uuid"] == str(escola_sp.uuid)
        uuids = {item["uuid"] for item in response.data}
        assert str(escola_outra.uuid) not in uuids
        
    def test_tipos_unidade_endpoint(
        self, api_client, user_gipe_admin
    ):
        """Endpoint tipos-unidade retorna todas as opções de tipo de unidade."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-tipos-unidade")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        tipos_retorno = {item["id"]: item["label"] for item in response.data}
        for choice in TipoUnidadeChoices.choices:
            assert choice[0] in tipos_retorno
            assert tipos_retorno[choice[0]] == choice[1]

    
@pytest.mark.django_db
class TestGestaoUnidadeViewSetRetrieve:
    """Testes para recuperação de unidade específica."""

    def test_retrieve_gipe_pode_ver_qualquer_unidade(
        self, api_client, user_gipe_admin, escola_sp
    ):
        """GIPE admin pode ver qualquer unidade."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["uuid"] == str(escola_sp.uuid)
        assert response.data["nome"] == escola_sp.nome

    def test_retrieve_ponto_focal_pode_ver_sua_unidade(
        self, api_client, user_pf_admin, escola_sp
    ):
        """Ponto Focal pode ver unidades da sua DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["uuid"] == str(escola_sp.uuid)

    def test_retrieve_ponto_focal_nao_pode_ver_unidade_de_outra_dre(
        self, api_client, user_pf_admin, escola_outra
    ):
        """Ponto Focal não pode ver unidades de outra DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_outra.uuid})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_usuario_comum_nao_pode_ver(
        self, api_client, user_comum, escola_sp
    ):
        """Usuário comum não pode ver unidades."""
        api_client.force_authenticate(user=user_comum)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_unidade_inexistente(
        self, api_client, user_gipe_admin
    ):
        """Retorna 400 para unidade inexistente."""
        import uuid
        fake_uuid = uuid.uuid4()

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": fake_uuid})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_usa_serializer_lista(
        self, api_client, user_gipe_admin, escola_sp
    ):
        """Retrieve deve usar GestaoUnidadeListaSerializer."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verifica campos do serializer de lista
        assert "tipo_unidade_label" in response.data
        assert "rede_label" in response.data
        assert "dre_nome" in response.data
        assert "dre_uuid" in response.data


@pytest.mark.django_db
class TestGestaoUnidadeViewSetCreate:
    """Testes para criação de unidades."""

    def test_create_dre_gipe_admin(
        self, api_client, user_gipe_admin
    ):
        """GIPE admin pode criar DRE."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        data = {
            "tipo_unidade": TipoUnidadeChoices.DRE,
            "nome": "Nova DRE",
            "rede": "DIRETA",
            "codigo_eol": "888888",
            "sigla": "NDRE",
            "ativa": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["nome"] == "Nova DRE"
        assert response.data["tipo_unidade"] == TipoUnidadeChoices.DRE
        assert Unidade.objects.filter(codigo_eol="888888").exists()

    def test_create_escola_gipe_admin(
        self, api_client, user_gipe_admin, dre_sp
    ):
        """GIPE admin pode criar escola."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEI,
            "nome": "Nova EMEI",
            "rede": "DIRETA",
            "codigo_eol": "999999",
            "dre": str(dre_sp.uuid),
            "sigla": "NEMI",
            "ativa": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["nome"] == "Nova EMEI"
        nova_unidade = Unidade.objects.get(codigo_eol="999999")
        assert nova_unidade.dre == dre_sp

    def test_create_escola_ponto_focal_sua_dre(
        self, api_client, user_pf_admin, dre_sp
    ):
        """Ponto Focal pode criar escola na sua DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-list")

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEI,
            "nome": "EMEI PF",
            "rede": "DIRETA",
            "codigo_eol": "777777",
            "dre": str(dre_sp.uuid),
            "sigla": "EPF",
            "ativa": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["nome"] == "EMEI PF"

    def test_create_escola_ponto_focal_outra_dre(
        self, api_client, user_pf_admin, dre_outra
    ):
        """Ponto Focal não pode criar escola em outra DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-list")

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEI,
            "nome": "EMEI Outra",
            "rede": "DIRETA",
            "codigo_eol": "666666",
            "dre": str(dre_outra.uuid),
            "sigla": "EOU",
            "ativa": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Ponto Focal só pode cadastrar unidades na sua DRE" in str(response.data)

    def test_create_dados_invalidos(
        self, api_client, user_gipe_admin
    ):
        """Retorna erro com dados inválidos."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEI,
            # Falta nome, codigo_eol, dre
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_create_codigo_eol_duplicado(
        self, api_client, user_gipe_admin, escola_sp
    ):
        """Não permite criar unidade com código EOL duplicado."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-list")

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEI,
            "nome": "Outra EMEI",
            "rede": "DIRETA",
            "codigo_eol": escola_sp.codigo_eol,  # Duplicado
            "dre": str(escola_sp.dre.uuid),
            "sigla": "OEM",
            "ativa": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestGestaoUnidadeViewSetUpdate:
    """Testes para atualização de unidades."""

    def test_update_full_gipe_admin(
        self, api_client, user_gipe_admin, escola_sp, dre_sp
    ):
        """GIPE admin pode fazer update completo."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEF,
            "nome": "EMEF Atualizada",
            "rede": "INDIRETA",
            "codigo_eol": escola_sp.codigo_eol,
            "dre": str(dre_sp.uuid),
            "sigla": "EMFA",
            "ativa": False,
        }

        response = api_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["nome"] == "EMEF Atualizada"
        assert response.data["tipo_unidade"] == TipoUnidadeChoices.EMEF
        escola_sp.refresh_from_db()
        assert escola_sp.nome == "EMEF Atualizada"

    def test_update_parcial_gipe_admin(
        self, api_client, user_gipe_admin, escola_sp, dre_sp
    ):
        """GIPE admin pode fazer update parcial."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        data = {
            "nome": "Nome Atualizado",
            "dre": str(dre_sp.uuid),
        }

        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["nome"] == "Nome Atualizado"
        escola_sp.refresh_from_db()
        assert escola_sp.nome == "Nome Atualizado"

    def test_update_ponto_focal_sua_unidade(
        self, api_client, user_pf_admin, escola_sp, dre_sp
    ):
        """Ponto Focal pode atualizar unidades da sua DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        data = {
            "nome": "Nome PF",
            "dre": str(dre_sp.uuid),
        }

        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["nome"] == "Nome PF"

    def test_update_ponto_focal_unidade_de_outra_dre(
        self, api_client, user_pf_admin, escola_outra, dre_outra
    ):
        """Ponto Focal não pode atualizar unidades de outra DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_outra.uuid})

        data = {
            "nome": "Tentativa",
            "dre": str(dre_outra.uuid),
        }

        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_usuario_comum_negado(
        self, api_client, user_comum, escola_sp, dre_sp
    ):
        """Usuário comum não pode atualizar."""
        api_client.force_authenticate(user=user_comum)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        data = {
            "nome": "Tentativa",
            "dre": str(dre_sp.uuid),
        }

        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestGestaoUnidadeViewSetDelete:
    """Testes para exclusão de unidades."""

    def test_delete_gipe_admin(
        self, api_client, user_gipe_admin, escola_sp
    ):
        """GIPE admin pode deletar unidade."""
        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})
        uuid_escola = escola_sp.uuid

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Unidade.objects.filter(uuid=uuid_escola).exists()

    def test_delete_ponto_focal_sua_unidade(
        self, api_client, user_pf_admin, escola_sp
    ):
        """Ponto Focal pode deletar unidades da sua DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})
        uuid_escola = escola_sp.uuid

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Unidade.objects.filter(uuid=uuid_escola).exists()

    def test_delete_ponto_focal_unidade_de_outra_dre(
        self, api_client, user_pf_admin, escola_outra
    ):
        """Ponto Focal não pode deletar unidades de outra DRE."""
        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_outra.uuid})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Unidade.objects.filter(uuid=escola_outra.uuid).exists()

    def test_delete_usuario_comum_negado(
        self, api_client, user_comum, escola_sp
    ):
        """Usuário comum não pode deletar."""
        api_client.force_authenticate(user=user_comum)
        url = reverse("unidades:gestao-unidades-detail", kwargs={"uuid": escola_sp.uuid})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Unidade.objects.filter(uuid=escola_sp.uuid).exists()


@pytest.mark.django_db
class TestGestaoUnidadeViewSetInativar:
    """Testes para a action inativar."""

    def test_inativar_unidade_ponto_focal_outra_dre(
        self, api_client, user_pf_admin, escola_outra
    ):
        """Ponto Focal não pode inativar unidades de outra DRE."""
        escola_outra.ativa = True
        escola_outra.save()

        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-inativar", kwargs={"uuid": escola_outra.uuid})

        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        escola_outra.refresh_from_db()
        assert escola_outra.ativa is True

    def test_inativar_unidade_usuario_comum_negado(
        self, api_client, user_comum, escola_sp
    ):
        """Usuário comum não pode inativar unidade."""
        escola_sp.ativa = True
        escola_sp.save()

        api_client.force_authenticate(user=user_comum)
        url = reverse("unidades:gestao-unidades-inativar", kwargs={"uuid": escola_sp.uuid})

        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        escola_sp.refresh_from_db()
        assert escola_sp.ativa is True

    def test_inativar_unidade_inexistente(
        self, api_client, user_gipe_admin
    ):
        """Retorna 400 ao tentar inativar unidade inexistente."""
        import uuid
        fake_uuid = uuid.uuid4()

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-inativar", kwargs={"uuid": fake_uuid})

        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_inativar_sem_motivo_retorna_400(
        self, api_client, user_gipe_admin, escola_sp
    ):
        escola_sp.ativa = True
        escola_sp.save()

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-inativar", kwargs={"uuid": escola_sp.uuid})

        response = api_client.post(url, data={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Motivo inativação é obrigatória" in response.data["detail"]

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is True
    
    @patch("apps.unidades.services.gestao_unidade_service.InativarUnidadeService.executar")
    def test_inativar_com_sucesso(
        self, mock_executar, api_client, user_gipe_admin, escola_sp
    ):
        escola_sp.ativa = True
        escola_sp.save()

        mock_executar.return_value = None

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-inativar", kwargs={"uuid": escola_sp.uuid})

        response = api_client.post(url, data={"motivo_inativacao": "Encerramento"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Unidade e usuários inativados com sucesso."

        mock_executar.assert_called_once()


@pytest.mark.django_db
class TestGestaoUnidadeViewSetReativar:
    """Testes para a action reativar."""

    def test_reativar_unidade_ponto_focal_outra_dre(
        self, api_client, user_pf_admin, escola_outra
    ):
        """Ponto Focal não pode reativar unidades de outra DRE."""
        escola_outra.ativa = False
        escola_outra.save()

        api_client.force_authenticate(user=user_pf_admin)
        url = reverse("unidades:gestao-unidades-reativar", kwargs={"uuid": escola_outra.uuid})

        response = api_client.post(url, data={"motivo_reativacao": "Reabertura"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        escola_outra.refresh_from_db()
        assert escola_outra.ativa is False

    def test_reativar_unidade_usuario_comum_negado(
        self, api_client, user_comum, escola_sp
    ):
        """Usuário comum não pode reativar unidade."""
        escola_sp.ativa = False
        escola_sp.save()

        api_client.force_authenticate(user=user_comum)
        url = reverse("unidades:gestao-unidades-reativar", kwargs={"uuid": escola_sp.uuid})

        response = api_client.post(url, data={"motivo_reativacao": "Reabertura"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        escola_sp.refresh_from_db()
        assert escola_sp.ativa is False

    def test_reativar_unidade_inexistente(
        self, api_client, user_gipe_admin
    ):
        """Retorna 400 ao tentar reativar unidade inexistente."""
        import uuid
        fake_uuid = uuid.uuid4()

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-reativar", kwargs={"uuid": fake_uuid})

        response = api_client.post(url, data={"motivo_reativacao": "Reabertura"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reativar_sem_motivo_retorna_400(
        self, api_client, user_gipe_admin, escola_sp
    ):
        escola_sp.ativa = False
        escola_sp.save()

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-reativar", kwargs={"uuid": escola_sp.uuid})

        response = api_client.post(url, data={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "motivo" in response.data["detail"].lower()

        escola_sp.refresh_from_db()
        assert escola_sp.ativa is False

    @patch("apps.unidades.services.gestao_unidade_service.ReativarUnidadeService.executar")
    def test_reativar_com_sucesso(
        self, mock_executar, api_client, user_gipe_admin, escola_sp
    ):
        escola_sp.ativa = False
        escola_sp.save()

        mock_executar.return_value = None

        api_client.force_authenticate(user=user_gipe_admin)
        url = reverse("unidades:gestao-unidades-reativar", kwargs={"uuid": escola_sp.uuid})

        response = api_client.post(url, data={"motivo_reativacao": "Reabertura"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Unidade reativada com sucesso."

        mock_executar.assert_called_once()

PATCH_PATH = (
    "apps.unidades.api.views.gestao_unidade_viewset."
    "ConsultaDadosEolService.consultar_dados_unidade"
)


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

@pytest.mark.django_db
class TestUnidadeViewSetConsultarEOL:

    @pytest.fixture
    def cargo_gipe(self, db):
        return Cargo.objects.create(codigo=User.PERFIL_GIPE, nome="GIPE")

    @pytest.fixture
    def cargo_ponto_focal(self, db):
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

        response = api_client.get(f"/api/unidades/gestao-unidades/consultar-eol/?codigo_eol={dre.pk}")

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

        response = api_client.get(f"/api/unidades/gestao-unidades/consultar-eol/?codigo_eol={ue_indireta.pk}")

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

        response = api_client.get(f"/api/unidades/gestao-unidades/consultar-eol/?codigo_eol={ue_indireta.pk}")

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

        response = api_client.get(f"/api/unidades/gestao-unidades/consultar-eol/?codigo_eol={dre.pk}")

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

        response = api_client.get(f"/api/unidades/gestao-unidades/consultar-eol/?codigo_eol={ue_indireta.pk}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "A unidade não pertence à sua DRE" in response.data["detail"]

    @patch(PATCH_PATH)
    def test_consultar_eol_servico_erro(
        self, mock_consulta, api_client, usuario_gipe, ue_indireta
    ):
        api_client.force_authenticate(usuario_gipe)

        mock_consulta.side_effect = Exception("Erro no EOL")

        response = api_client.get(f"/api/unidades/gestao-unidades/consultar-eol/?codigo_eol={ue_indireta.pk}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Erro no EOL"

    @patch(PATCH_PATH)
    def test_gipe_dre_nao_cadastrada_no_sistema(
        self, mock_consulta, api_client, usuario_gipe, ue_indireta
    ):
        api_client.force_authenticate(usuario_gipe)

        Unidade.objects.filter(codigo_eol="999999").delete()

        mock_consulta.return_value = {
            "codigo": "222222",
            "codigoDRE": "999999",
            "siglaTipoEscola": "CEI ",
            "nomeExibicao": "UE Indireta",
        }

        response = api_client.get(
            f"/api/unidades/gestao-unidades/consultar-eol/?codigo_eol={ue_indireta.pk}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Diretoria Regional não encontrada!" in response.data["detail"]