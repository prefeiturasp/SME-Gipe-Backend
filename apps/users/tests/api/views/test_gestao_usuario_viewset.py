import pytest
import uuid
from django.utils import timezone
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.unidades.models.unidades import TipoGestaoChoices
from apps.helpers.exceptions import IntercorrenciasDeletionError

User = get_user_model()


@pytest.fixture
def usuario_validado(cargo_comum):
    """Usuário já aprovado."""
    return User.objects.create_user(
        username="usuario_validado",
        name="Usuario Validado",
        email="validado@example.com",
        cpf="12345678999",
        cargo=cargo_comum,
        rede=TipoGestaoChoices.INDIRETA,
        is_validado=True,
        data_aprovacao=timezone.now(),
        responsavel_aprovacao="admin_gipe",
    )

@pytest.fixture
def usuario_inativo(cargo_comum):
    """Usuário inativo."""
    return User.objects.create(
        username="usuario_inativo",
        cpf="11122233344",
        name="Usuário Inativo",
        cargo=cargo_comum,
        is_active=False,
        data_inativacao=timezone.now(),
        responsavel_inativacao="ADMIN001",
    )

@pytest.mark.django_db
def test_list_anonymous_negado(api_client):
    """Usuário anônimo não pode listar usuários."""
    response = api_client.get("/api/users/gestao-usuarios/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_anonymous_negado(api_client, cargo_comum):
    """Usuário anônimo não pode criar usuários."""
    data = {
        "username": "novo_user",
        "email": "novo@example.com",
        "cpf": "99999999999",
        "cargo": cargo_comum.pk,
    }
    response = api_client.post("/api/users/gestao-usuarios/", data)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_usuario_comum_negado(api_client, user_comum):
    """Usuário comum sem is_app_admin não pode listar usuários."""
    api_client.force_authenticate(user=user_comum)
    response = api_client.get("/api/users/gestao-usuarios/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_usuario_comum_negado(api_client, user_comum, cargo_comum):
    """Usuário comum não pode criar usuários."""
    api_client.force_authenticate(user=user_comum)
    data = {
        "username": "novo_user",
        "email": "novo@example.com",
        "cpf": "99999999999",
        "cargo": cargo_comum.pk,
    }
    response = api_client.post("/api/users/gestao-usuarios/", data)
    assert response.status_code == status.HTTP_403_FORBIDDEN



@pytest.mark.django_db
def test_list_gipe_admin_ve_todos_usuarios(
    api_client, user_gipe_admin, usuario_dre_sp, usuario_dre_outra, user_pf_admin
):
    """GIPE admin vê todos os usuários do sistema."""
    api_client.force_authenticate(user=user_gipe_admin)
    response = api_client.get("/api/users/gestao-usuarios/")

    assert response.status_code == status.HTTP_200_OK
    usernames = [u["username"] for u in response.data]

    assert "gipe_admin" in usernames
    assert "usuario_dre_sp" in usernames
    assert "usuario_dre_outra" in usernames
    assert "pf_admin" in usernames


@pytest.mark.django_db
def test_list_gipe_admin_filtra_por_dre(
    api_client, user_gipe_admin, user_comum, outro_user_comum, dre_sp
):
    """Filtro 'dre' retorna somente usuários daquela DRE para o GIPE."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.get(
        f"/api/users/gestao-usuarios/?dre={dre_sp.uuid}"
    )

    assert response.status_code == status.HTTP_200_OK
    usernames = [u["username"] for u in response.data]

    assert "user_comum" in usernames
    assert "outro_user" not in usernames


@pytest.mark.django_db
def test_list_filtra_por_unidade(
    api_client, user_gipe_admin, user_comum, outro_user_comum, escola_sp
):
    """Filtro por unidade limita a listagem ao usuário da unidade informada."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.get(
        f"/api/users/gestao-usuarios/?unidade={escola_sp.uuid}"
    )

    assert response.status_code == status.HTTP_200_OK
    usernames = [u["username"] for u in response.data]

    assert usernames == ["user_comum"]


@pytest.mark.django_db
def test_list_filtra_por_ativo_false(api_client, user_gipe_admin, cargo_comum):
    """Filtro 'ativo=false' retorna apenas usuários inativos."""
    user_inativo = User.objects.create_user(
        username="usuario_inativo",
        email="inativo@example.com",
        cpf="98989898989",
        cargo=cargo_comum,
        is_active=False,
    )

    api_client.force_authenticate(user=user_gipe_admin)
    response = api_client.get("/api/users/gestao-usuarios/?ativo=false")

    assert response.status_code == status.HTTP_200_OK
    assert [u["username"] for u in response.data] == [user_inativo.username]


@pytest.mark.django_db
def test_list_filtra_pendentes_aprovacao_indireta(
    api_client, user_gipe_admin, usuario_nao_validado, cargo_comum
):
    """Filtro 'pendente_aprovacao' limita a usuários indiretos não validados."""
    usuario_nao_validado.rede = TipoGestaoChoices.INDIRETA
    usuario_nao_validado.save()

    User.objects.create_user(
        username="usuario_indireta_validado",
        email="indireta.validado@example.com",
        cpf="97979797979",
        cargo=cargo_comum,
        rede=TipoGestaoChoices.INDIRETA,
        is_validado=True,
    )

    api_client.force_authenticate(user=user_gipe_admin)
    response = api_client.get("/api/users/gestao-usuarios/?pendente_aprovacao=true")

    assert response.status_code == status.HTTP_200_OK
    assert [u["username"] for u in response.data] == ["nao_validado"]



@pytest.mark.django_db
def test_retrieve_usuario_nao_gipe_nao_pf_acessa_proprio_registro(
    api_client, cargo_comum, usuario_dre_sp
):
    """
    Usuário não-admin que não é GIPE nem PF pode ver apenas seu próprio registro.
    Cobre a linha: return self.queryset.filter(uuid=user.uuid)
    """

    user_comum = User.objects.create_user(
        username="comum_simples",
        email="comum.simples@example.com",
        cpf="88888888881",
        cargo=cargo_comum,
        is_app_admin=False,  
    )
    
    api_client.force_authenticate(user=user_comum)
    
    # Tenta acessar seu próprio registro
    response = api_client.get(f"/api/users/gestao-usuarios/{user_comum.uuid}/")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "comum_simples"
    
    response_outro = api_client.get(f"/api/users/gestao-usuarios/{usuario_dre_sp.uuid}/")
    assert response_outro.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_gipe_admin_cria_usuario(api_client, user_gipe_admin, cargo_comum, escola_sp):
    """GIPE admin pode criar novos usuários."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    data = {
        "username": "novo_usuario",
        "name": "Novo Usuario",
        "email": "novo.usuario@example.com",
        "cpf": "88888888888",
        "cargo": cargo_comum.pk,
        "unidades": [escola_sp.codigo_eol],
        "is_app_admin": False,
    }
    
    response = api_client.post("/api/users/gestao-usuarios/", data, format="json")
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["username"] == "novo_usuario"
    assert response.data["email"] == "novo.usuario@example.com"
    
    user = User.objects.get(username="novo_usuario")
    assert user.cpf == "88888888888"
    assert user.cargo.pk == cargo_comum.pk


@pytest.mark.django_db
def test_create_pf_admin_nao_pode_criar_em_outra_dre(
    api_client, user_pf_admin, cargo_comum, escola_outra
):
    """PF admin não pode criar usuários em unidades de outras DREs."""
    api_client.force_authenticate(user=user_pf_admin)
    
    data = {
        "username": "novo_usuario_outra_dre",
        "name": "Usuario Outra DRE",
        "email": "novo.outra@example.com",
        "cpf": "88888888890",
        "cargo": cargo_comum.pk,
        "unidades": [escola_outra.codigo_eol],
        "is_app_admin": False,
    }
    
    response = api_client.post("/api/users/gestao-usuarios/", data, format="json")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.data


@pytest.mark.django_db
def test_create_pf_admin_nao_pode_atribuir_outra_dre(
    api_client, user_pf_admin, cargo_comum, dre_outra
):
    """PF admin não pode atribuir usuário diretamente a outra DRE."""
    api_client.force_authenticate(user=user_pf_admin)
    
    data = {
        "username": "novo_pf_outra_dre",
        "name": "Novo PF Outra DRE",
        "email": "novo.pf.outra@example.com",
        "cpf": "77777777777",
        "cargo": cargo_comum.pk,
        "unidades": [dre_outra.codigo_eol],
        "is_app_admin": False,
    }
    
    response = api_client.post("/api/users/gestao-usuarios/", data, format="json")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.data
    assert "Ponto Focal só pode cadastrar usuários para sua própria DRE" in response.data["detail"]


@pytest.mark.django_db
def test_retrieve_gipe_admin_ve_qualquer_usuario(
    api_client, user_gipe_admin, usuario_dre_sp
):
    """GIPE admin pode visualizar detalhes de qualquer usuário."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    response = api_client.get(f"/api/users/gestao-usuarios/{usuario_dre_sp.uuid}/")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "usuario_dre_sp"


@pytest.mark.django_db
def test_retrieve_pf_admin_nao_ve_usuario_de_outra_dre(
    api_client, user_pf_admin, usuario_dre_outra
):
    """PF admin não pode visualizar usuário de outra DRE."""
    api_client.force_authenticate(user=user_pf_admin)
    
    response = api_client.get(f"/api/users/gestao-usuarios/{usuario_dre_outra.uuid}/")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN



@pytest.mark.django_db
def test_update_pf_admin_nao_atualiza_usuario_de_outra_dre(
    api_client, user_pf_admin, usuario_dre_outra
):
    """PF admin não pode atualizar usuário de outra DRE."""
    api_client.force_authenticate(user=user_pf_admin)
    
    data = {
        "username": "usuario_dre_outra",
        "email": "novo.email@example.com",
        "cpf": usuario_dre_outra.cpf,
        "cargo": usuario_dre_outra.cargo.pk,
    }
    
    response = api_client.put(
        f"/api/users/gestao-usuarios/{usuario_dre_outra.uuid}/", 
        data, 
        format="json"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_partial_update_gipe_admin(api_client, user_gipe_admin, usuario_dre_sp):
    """GIPE admin pode fazer update parcial."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    data = {"email": "parcial@example.com"}
    
    response = api_client.patch(
        f"/api/users/gestao-usuarios/{usuario_dre_sp.uuid}/", 
        data, 
        format="json"
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == "parcial@example.com"
    assert response.data["username"] == "usuario_dre_sp"  # Não mudou



@pytest.mark.django_db
def test_delete_gipe_admin_remove_usuario(api_client, user_gipe_admin, usuario_dre_sp):
    """GIPE admin pode deletar usuários."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    response = api_client.delete(f"/api/users/gestao-usuarios/{usuario_dre_sp.uuid}/")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(uuid=usuario_dre_sp.uuid).exists()


@pytest.mark.django_db
def test_aprovar_pf_admin_nao_aprova_usuario_de_outra_dre(
    api_client, user_pf_admin, usuario_nao_validado, escola_outra
):
    """PF admin não pode aprovar usuário de outra DRE."""

    usuario_nao_validado.unidades.clear()
    usuario_nao_validado.unidades.add(escola_outra)
    
    api_client.force_authenticate(user=user_pf_admin)
    
    response = api_client.post(f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/aprovar/")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_aprovar_diretor_nao_pode_aprovar(
    api_client, user_diretor, usuario_nao_validado
):
    """Diretor não pode aprovar usuários (falta permissão CanApproveUser)."""
    user_diretor.is_app_admin = True
    user_diretor.save()
    
    api_client.force_authenticate(user=user_diretor)
    
    response = api_client.post(f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/aprovar/")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_aprovar_usuario_comum_nao_pode_aprovar(
    api_client, user_comum, usuario_nao_validado
):
    """Usuário comum não pode aprovar."""
    api_client.force_authenticate(user=user_comum)
    
    response = api_client.post(f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/aprovar/")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_aprovar_usuario_ja_aprovado_retorna_400(
    api_client, user_gipe_admin, usuario_validado
):
    """Não permite aprovar usuário já aprovado."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_validado.uuid}/aprovar/"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Usuário já está aprovado."


@pytest.mark.django_db
@patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_aprovar_usuario_erro_core_sso(
    mock_cria_usuario,
    api_client,
    user_gipe_admin,
    usuario_nao_validado,
):
    """Erro no Core SSO impede aprovação do usuário."""
    mock_cria_usuario.side_effect = Exception("Erro Core SSO")

    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/aprovar/"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Erro ao criar o usuário no Core SSO."

    usuario_nao_validado.refresh_from_db()
    assert usuario_nao_validado.is_validado is False


@pytest.mark.django_db
@patch("apps.users.services.envia_email_service.EnviaEmailService.enviar")
@patch("apps.users.services.usuario_core_sso_service.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_aprovar_usuario_com_sucesso(
    mock_cria_usuario,
    mock_envia_email,
    api_client,
    user_gipe_admin,
    usuario_nao_validado,
):
    """Aprova usuário com sucesso."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/aprovar/"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "Usuário aprovado com sucesso."

    usuario_nao_validado.refresh_from_db()

    assert usuario_nao_validado.is_validado is True
    assert usuario_nao_validado.data_aprovacao is not None
    assert usuario_nao_validado.responsavel_aprovacao == str(user_gipe_admin)

    mock_cria_usuario.assert_called_once()
    mock_envia_email.assert_called_once()


@pytest.mark.django_db
@patch("apps.users.services.envia_email_service.EnviaEmailService.enviar")
def test_reprovar_usuario_com_sucesso(
    mock_envia_email,
    api_client,
    user_gipe_admin,
    usuario_nao_validado,
):
    """Reprova usuário com sucesso."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/reprovar/",
        data={"justificativa": "Cadastro incompleto"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "Usuário reprovado com sucesso."

    assert not User.objects.filter(uuid=usuario_nao_validado.uuid).exists()
    mock_envia_email.assert_called_once()


@pytest.mark.django_db
def test_reprovar_usuario_sem_justificativa_retorna_400(
    api_client,
    user_gipe_admin,
    usuario_nao_validado,
):
    """Justificativa é obrigatória para reprovação."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/reprovar/",
        data={},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Justificativa é obrigatória para reprovação."


@pytest.mark.django_db
def test_reprovar_usuario_ja_aprovado_retorna_400(
    api_client,
    user_gipe_admin,
    usuario_validado,
):
    """Usuário aprovado não pode ser reprovado."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_validado.uuid}/reprovar/",
        data={"justificativa": "Erro"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Usuário já aprovado não pode ser reprovado."


@pytest.mark.django_db
def test_reprovar_usuario_sem_permissao_retorna_403(
    api_client,
    user_comum,
    usuario_nao_validado,
):
    """Usuário comum não pode reprovar."""
    api_client.force_authenticate(user=user_comum)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/reprovar/",
        data={"justificativa": "Teste"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_inativar_usuario_sem_permissao_retorna_403(
    api_client,
    user_comum,
    usuario_validado,
):
    """Usuário sem permissão não pode inativar outro usuário."""
    api_client.force_authenticate(user=user_comum)

    response = api_client.put(
        f"/api/users/gestao-usuarios/{usuario_validado.uuid}/inativar/"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_inativar_usuario_com_sucesso(
    api_client,
    user_gipe_admin,
    usuario_validado,
):
    """Usuário com permissão consegue inativar um usuário."""
    api_client.force_authenticate(user=user_gipe_admin)

    with patch(
        "apps.users.services.gestao_usuario_service.InativarUsuarioService.inativar"
    ) as mock_inativar:

        response = api_client.post(
            f"/api/users/gestao-usuarios/{usuario_validado.uuid}/inativar/",
            data={"motivo_inativacao": "Teste"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Usuário inativado com sucesso."

        mock_inativar.assert_called_once_with(
            usuario_a_ser_inativado=usuario_validado,
            usuario_responsavel=str(user_gipe_admin),
            motivo_inativacao="Teste",
            flag_via_unidade=False
        )


@pytest.mark.django_db
def test_inativar_usuario_inexistente_retorna_404(
    api_client,
    user_gipe_admin,
):
    """Retorna 404 ao tentar inativar um usuário que não existe."""
    api_client.force_authenticate(user=user_gipe_admin)

    fake_uuid = "11111111-1111-1111-1111-111111111111"

    response = api_client.post(
        f"/api/users/gestao-usuarios/{fake_uuid}/inativar/"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Usuário não encontrado."


@pytest.mark.django_db
def test_inativar_usuario_uuid_invalido_retorna_400(
    api_client,
    user_gipe_admin,
):
    """Retorna 400 quando o UUID informado é inválido."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        "/api/users/gestao-usuarios/uuid-invalido/inativar/"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "UUID informado é inválido."
    

@pytest.mark.django_db
def test_inativar_usuario_sem_motivo_inativacao_retorna_400(
    api_client,
    user_gipe_admin,
):
    """Motivo inativacao é obrigatória para inativação."""
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{user_gipe_admin.uuid}/inativar/",
        data={},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Motivo inativação é obrigatória para executar a inativação."


@pytest.mark.django_db
def test_inativar_usuario_falha_intercorrencias_retorna_400(
    api_client,
    user_gipe_admin,
    usuario_validado,
):
    """Falha ao deletar intercorrencias retorna 400."""
    api_client.force_authenticate(user=user_gipe_admin)

    with patch(
        "apps.users.api.views.gestao_usuario_viewset.InativarUsuarioService.inativar",
        side_effect=IntercorrenciasDeletionError("erro intercorrencias"),
    ):
        response = api_client.post(
            f"/api/users/gestao-usuarios/{usuario_validado.uuid}/inativar/",
            data={"motivo_inativacao": "Teste"},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Não foi possível inativar o usuário" in response.data["detail"]
    assert response.data["motivo"] == "Falha ao deletar intercorrências em preenchimento."
    assert response.data["erro_tecnico"] == "erro intercorrencias"


@pytest.mark.django_db
def test_inativar_usuario_erro_inesperado_retorna_500(
    api_client,
    user_gipe_admin,
    usuario_validado,
):
    """Erro inesperado ao inativar usuario retorna 500."""
    api_client.force_authenticate(user=user_gipe_admin)

    with patch(
        "apps.users.api.views.gestao_usuario_viewset.InativarUsuarioService.inativar",
        side_effect=Exception("boom"),
    ):
        response = api_client.post(
            f"/api/users/gestao-usuarios/{usuario_validado.uuid}/inativar/",
            data={"motivo_inativacao": "Teste"},
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["detail"] == "Erro inesperado ao inativar usuário."
    assert response.data["erro_tecnico"] == "boom"


@pytest.mark.django_db
def test_inativar_usuario_falha_envio_email_retorna_200(
    api_client,
    user_gipe_admin,
    usuario_validado,
):
    """Falha no envio de email nao reverte inativacao."""
    api_client.force_authenticate(user=user_gipe_admin)

    with patch(
        "apps.users.api.views.gestao_usuario_viewset.InativarUsuarioService.inativar"
    ), patch(
        "apps.users.api.views.gestao_usuario_viewset.EnviaEmailService.enviar",
        side_effect=Exception("email falhou"),
    ):
        response = api_client.post(
            f"/api/users/gestao-usuarios/{usuario_validado.uuid}/inativar/",
            data={"motivo_inativacao": "Teste"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "Usuário inativado com sucesso."


@pytest.mark.django_db
def test_retrieve_uuid_nao_existe_retorna_404(api_client, user_gipe_admin):
    """Buscar usuário com UUID válido mas não existente retorna 404."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    # UUID válido mas que não existe no banco
    uuid_inexistente = uuid.uuid4()
    
    response = api_client.get(f"/api/users/gestao-usuarios/{uuid_inexistente}/")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Usuário não encontrado" in str(response.data)


@pytest.mark.django_db
def test_update_uuid_nao_existe_retorna_404(api_client, user_gipe_admin, cargo_comum):
    """Atualizar usuário com UUID não existente retorna 404."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    uuid_inexistente = uuid.uuid4()
    
    data = {
        "username": "teste",
        "email": "teste@example.com",
        "cpf": "12345678901",
        "cargo": cargo_comum.pk,
    }
    
    response = api_client.put(
        f"/api/users/gestao-usuarios/{uuid_inexistente}/",
        data,
        format="json"
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_partial_update_uuid_nao_existe_retorna_404(api_client, user_gipe_admin):
    """Patch em usuário com UUID não existente retorna 404."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    uuid_inexistente = uuid.uuid4()
    
    data = {"email": "novo@example.com"}
    
    response = api_client.patch(
        f"/api/users/gestao-usuarios/{uuid_inexistente}/",
        data,
        format="json"
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_uuid_nao_existe_retorna_404(api_client, user_gipe_admin):
    """Deletar usuário com UUID não existente retorna 404."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    uuid_inexistente = uuid.uuid4()
    
    response = api_client.delete(f"/api/users/gestao-usuarios/{uuid_inexistente}/")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_aprovar_uuid_nao_existe_retorna_404(api_client, user_gipe_admin):
    """Aprovar usuário com UUID não existente retorna 404."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    uuid_inexistente = uuid.uuid4()
    
    response = api_client.post(f"/api/users/gestao-usuarios/{uuid_inexistente}/aprovar/")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_reprovar_uuid_nao_existe_retorna_404(api_client, user_gipe_admin):
    """Reprovar usuário com UUID não existente retorna 404."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    uuid_inexistente = uuid.uuid4()
    
    response = api_client.post(
        f"/api/users/gestao-usuarios/{uuid_inexistente}/reprovar/",
        data={"justificativa": "Teste"},
        format="json"
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_reativar_usuario_com_sucesso_retorna_200(
    api_client,
    user_gipe_admin,
    usuario_inativo,
):
    api_client.force_authenticate(user=user_gipe_admin)

    with patch(
        "apps.users.services.gestao_usuario_service.ReativarUsuarioService.reativar"
    ) as mock_reativar:
        response = api_client.post(
            f"/api/users/gestao-usuarios/{usuario_inativo.uuid}/reativar/"
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "Usuário reativado com sucesso."

    mock_reativar.assert_called_once_with(
        usuario_a_ser_reativado=usuario_inativo
    )


@pytest.mark.django_db
def test_reativar_usuario_sem_permissao_retorna_403(
    api_client,
    user_comum,
    usuario_inativo,
):
    api_client.force_authenticate(user=user_comum)

    response = api_client.post(
        f"/api/users/gestao-usuarios/{usuario_inativo.uuid}/reativar/"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    

@pytest.mark.django_db
def test_reativar_usuario_uuid_invalido_retorna_404(
    api_client,
    user_gipe_admin,
):
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.post(
        "/api/users/gestao-usuarios/uuid-invalido/reativar/"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "UUID informado é inválido."

@pytest.mark.django_db
def test_list_admin_nao_ve_superusuarios(
    api_client,
    user_gipe_admin
):
    """
    Não deve ver superusuários na listagem.
    """
    api_client.force_authenticate(user=user_gipe_admin)

    response = api_client.get("/api/users/gestao-usuarios/")

    assert response.status_code == status.HTTP_200_OK

    usernames = [u["username"] for u in response.data]

    assert "superuser" not in usernames

@pytest.mark.django_db
def test_consultar_core_sso_rf_valido_retorna_200(api_client, user_gipe_admin):
    api_client.force_authenticate(user=user_gipe_admin)

    mock_retorno = {
        "login": "123456",
        "nome": "teste usuario",
        "email": "usuario@teste.com",
    }

    with patch(
        "apps.users.api.views.gestao_usuario_viewset.SmeIntegracaoService.usuario_core_sso_or_none",
        return_value=mock_retorno,
    ):
        response = api_client.get(
            "/api/users/gestao-usuarios/consultar-core-sso/?rf=123456"
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == mock_retorno

@pytest.mark.django_db
def test_consultar_core_sso_rf_invalido_retorna_404(api_client, user_gipe_admin):
    api_client.force_authenticate(user=user_gipe_admin)

    with patch(
        "apps.users.api.views.gestao_usuario_viewset.SmeIntegracaoService.usuario_core_sso_or_none",
        return_value=None,
    ):
        response = api_client.get(
            "/api/users/gestao-usuarios/consultar-core-sso/?rf=000000"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "RF inválido!" in response.data["detail"]

@pytest.mark.django_db
def test_consultar_core_sso_erro_inesperado_retorna_400(api_client, user_gipe_admin):
    api_client.force_authenticate(user=user_gipe_admin)

    with patch(
        "apps.users.api.views.gestao_usuario_viewset.SmeIntegracaoService.usuario_core_sso_or_none",
        side_effect=Exception("Falha na integração"),
    ):
        response = api_client.get(
            "/api/users/gestao-usuarios/consultar-core-sso/?rf=123456"
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Falha na integração"