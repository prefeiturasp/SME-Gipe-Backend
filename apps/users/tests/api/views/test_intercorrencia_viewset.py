import pytest
from unittest.mock import patch
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model

from apps.users.api.views.intercorrencia_viewset import (
    IntercorrenciaViewSet,
    CargoEnum,
)
from apps.users.models import Cargo

User = get_user_model()


@pytest.mark.django_db
@patch("apps.users.permissions.IsInternalServiceRequest.has_permission", return_value=True)
class TestIntercorrenciaViewSet:

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.view = IntercorrenciaViewSet.as_view({
            "post": "alerta_finalizacao_ocorrencia"
        })
        self.url = "/fake-url/"

    def criar_usuario(self, username, email, codigo_cargo):
        cargo = Cargo.objects.create(codigo=codigo_cargo, nome="Cargo Teste")
        return User.objects.create(
            username=username,
            email=email,
            cargo=cargo
        )

    def test_payload_invalido_retorna_400(self, _mock_perm):
        request = self.factory.post(self.url, data={})

        response = self.view(request)

        assert response.status_code == 400
        assert response.data["success"] is False

    def test_usuario_nao_encontrado_retorna_404(self, _mock_perm):
        request = self.factory.post(self.url, data={
            "username": "nao_existe",
            "data_ocorrencia": "2024-01-01",
            "uuid_ocorrencia": "123"
        })

        response = self.view(request)

        assert response.status_code == 404

    def test_usuario_sem_email_retorna_404(self, _mock_perm):
        user = self.criar_usuario("user_sem_email", "", CargoEnum.PONTO_FOCAL_DRE)

        request = self.factory.post(self.url, data={
            "username": user.username,
            "data_ocorrencia": "2024-01-01",
            "uuid_ocorrencia": "123"
        })

        response = self.view(request)

        assert response.status_code == 404

    def test_usuario_gipe_nao_envia_email(self, _mock_perm):
        user = self.criar_usuario("gipe_user", "gipe@test.com", CargoEnum.GIPE)

        request = self.factory.post(self.url, data={
            "username": user.username,
            "data_ocorrencia": "2024-01-01",
            "uuid_ocorrencia": "123"
        })

        response = self.view(request)

        assert response.status_code == 200
        assert "não é necessário" in response.data["message"]

    @patch("apps.users.api.views.intercorrencia_viewset.EnviaEmailService.enviar")
    def test_envio_email_sucesso_para_dre(self, mock_enviar, _mock_perm):
        user = self.criar_usuario("dre_user", "dre@test.com", CargoEnum.PONTO_FOCAL_DRE)

        request = self.factory.post(self.url, data={
            "username": user.username,
            "data_ocorrencia": "2024-01-01",
            "uuid_ocorrencia": "abc-123"
        })

        response = self.view(request)

        assert response.status_code == 200
        assert response.data["success"] is True

        _, kwargs = mock_enviar.call_args
        assert kwargs["template_html"] == "emails/finalizacao_intercorrencia.html"
        assert kwargs["destinatario"] == "dre@test.com"

    @patch("apps.users.api.views.intercorrencia_viewset.EnviaEmailService.enviar")
    def test_envio_email_sucesso_para_ue(self, mock_enviar, _mock_perm):
        user = self.criar_usuario("ue_user", "ue@test.com", CargoEnum.DIRETOR_DE_ESCOLA)

        request = self.factory.post(self.url, data={
            "username": user.username,
            "data_ocorrencia": "2024-01-01",
            "uuid_ocorrencia": "abc-123"
        })

        response = self.view(request)

        assert response.status_code == 200

        _, kwargs = mock_enviar.call_args
        assert kwargs["template_html"] == "emails/finalizacao_intercorrencia.html"

    @patch(
        "apps.users.api.views.intercorrencia_viewset.EnviaEmailService.enviar",
        side_effect=Exception("erro envio")
    )
    def test_erro_ao_enviar_email_retorna_500(self, _mock_enviar, _mock_perm):
        user = self.criar_usuario("erro_user", "erro@test.com", CargoEnum.DIRETOR_DE_ESCOLA)

        request = self.factory.post(self.url, data={
            "username": user.username,
            "data_ocorrencia": "2024-01-01",
            "uuid_ocorrencia": "abc-123"
        })

        response = self.view(request)

        assert response.status_code == 500
        assert response.data["success"] is False