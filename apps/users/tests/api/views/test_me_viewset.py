import pytest
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from apps.users.models import Cargo, User
from apps.users.api.views.me_viewset import MeView
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def cargo(db):
    return Cargo.objects.create(codigo=1234, nome="Cargo Teste")


@pytest.fixture
def dre(db):
    return Unidade.objects.create(
        codigo_eol="DRE001",
        nome="DRE Teste",
        tipo_unidade=TipoUnidadeChoices.DRE
    )


@pytest.fixture
def unidade(db, dre):
    return Unidade.objects.create(
        codigo_eol="UNI001",
        nome="Unidade Teste",
        tipo_unidade=TipoUnidadeChoices.IFSP,
        dre=dre,
        sigla="UT"
    )


@pytest.fixture
def user(db, cargo):
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        name="Test User",
        cargo=cargo
    )


@pytest.fixture
def user_with_unidade(db, cargo, unidade):
    user = User.objects.create_user(
        username="user2",
        email="user2@example.com",
        password="testpass123",
        name="User Two",
        cargo=cargo
    )
    user.unidades.add(unidade)
    return user


@pytest.mark.django_db
class TestMeView:

    def test_get_authenticated_user(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/users/me")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == user.username
        assert response.data["perfil_acesso"] == {"codigo": user.cargo.codigo, "nome": user.cargo.nome}
        assert response.data["unidades"] == []

    def test_get_authenticated_user_with_unidade(self, api_client, user_with_unidade, unidade):
        user = user_with_unidade
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/users/me")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["perfil_acesso"] == {
            "codigo": user.cargo.codigo,
            "nome": user.cargo.nome,
        }
        assert len(response.data["unidades"]) == 1
        unidade_data = response.data["unidades"][0]

        assert unidade_data["ue"]["codigo_eol"] == unidade.codigo_eol
        assert unidade_data["ue"]["nome"] == unidade.nome
        assert unidade_data["ue"]["sigla"] == unidade.sigla

        if unidade.dre:
            assert unidade_data["dre"]["codigo_eol"] == unidade.dre.codigo_eol
            assert unidade_data["dre"]["nome"] == unidade.dre.nome
            assert unidade_data["dre"]["sigla"] == unidade.dre.sigla
        else:
            assert unidade_data["dre"]["codigo_eol"] is None
            assert unidade_data["dre"]["nome"] is None
            assert unidade_data["dre"]["sigla"] is None

    def test_get_unauthenticated_user_api_client(self, api_client):
        response = api_client.get("/api/users/me")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_unauthenticated_user_direct_view(self, db):
        factory = APIRequestFactory()
        request = factory.get("/api/users/me")
        request.user = AnonymousUser()
        view = MeView.as_view()

        with patch.object(MeView, 'permission_classes', []):
            response = view(request)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.data["detail"] == "Não autenticado."

    def test_get_user_not_found(self, api_client, db, cargo):
        temp_user = User.objects.create_user(
            username="temp",
            email="temp@example.com",
            password="temp123",
            cargo=cargo,
            name="Temp User"
        )
        api_client.force_authenticate(user=temp_user)
        temp_user.delete()
        response = api_client.get("/api/users/me")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Usuário não encontrado."