import pytest
import importlib

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.api.views.verify_token_viewset import VerifyTokenFlexibleView

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def valid_token():
    return str(AccessToken.for_user(type("User", (), {"id": 1})()))


@pytest.mark.django_db
class TestVerifyTokenFlexibleView:

    endpoint = "/api/users/verify-token"

    def test_token_valido_no_body(self, api_client, valid_token):
        response = api_client.post(self.endpoint, {"token": valid_token}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Token válido."

    def test_token_ausente(self, api_client):
        response = api_client.post(self.endpoint, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token ausente" in response.data["detail"]

    def test_token_invalido(self, api_client):
        response = api_client.post(self.endpoint, {"token": "aaa.bbb.ccc"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.data["detail"].lower()

    def test_header_invalido(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer ???")
        response = api_client.post(self.endpoint, {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_header_malformado(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Token abc123")
        response = api_client.post(self.endpoint, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_valido_no_header(self, api_client, valid_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {valid_token}")
        response = api_client.post(self.endpoint, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Token válido."

    def test_header_decode_error(self, api_client, monkeypatch):
        view_mod = importlib.import_module(VerifyTokenFlexibleView.__module__)
        monkeypatch.setattr(view_mod, "get_authorization_header", lambda req: b"Bearer \x80abc")

        response = api_client.post(self.endpoint, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token ausente" in response.data["detail"]