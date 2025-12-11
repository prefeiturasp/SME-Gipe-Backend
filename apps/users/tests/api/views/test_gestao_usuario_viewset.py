import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.unidades.models.unidades import TipoGestaoChoices

User = get_user_model()



# ==========================================
# Testes de Permissão - Anonymous
# ==========================================

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


# ==========================================
# Testes de Permissão - Usuário Comum
# ==========================================

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


# ==========================================
# Testes de get_queryset - GIPE Admin
# ==========================================


@pytest.mark.django_db
def test_list_gipe_admin_ve_todos_usuarios(
    api_client, user_gipe_admin, usuario_dre_sp, usuario_dre_outra
):
    """GIPE admin vê todos os usuários do sistema."""
    api_client.force_authenticate(user=user_gipe_admin)
    response = api_client.get("/api/users/gestao-usuarios/")

    assert response.status_code == status.HTTP_200_OK
    usernames = [u["username"] for u in response.data]

    # Deve conter pelo menos os 3 usuários criados
    assert "gipe_admin" in usernames
    assert "usuario_dre_sp" in usernames
    assert "usuario_dre_outra" in usernames


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


# ==========================================
# Teste para cobrir linha 39 do viewset
# ==========================================

@pytest.mark.django_db
def test_retrieve_usuario_nao_gipe_nao_pf_acessa_proprio_registro(
    api_client, cargo_comum, usuario_dre_sp
):
    """
    Usuário não-admin que não é GIPE nem PF pode ver apenas seu próprio registro.
    Cobre a linha: return self.queryset.filter(uuid=user.uuid)
    """
    # Cria usuário comum (não é GIPE nem PF, não é admin)
    user_comum = User.objects.create_user(
        username="comum_simples",
        email="comum.simples@example.com",
        cpf="88888888881",
        cargo=cargo_comum,
        is_app_admin=False,  # Não é admin
    )
    
    api_client.force_authenticate(user=user_comum)
    
    # Tenta acessar seu próprio registro
    response = api_client.get(f"/api/users/gestao-usuarios/{user_comum.uuid}/")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "comum_simples"
    
    # Tenta acessar registro de outro usuário (deve falhar)
    response_outro = api_client.get(f"/api/users/gestao-usuarios/{usuario_dre_sp.uuid}/")
    assert response_outro.status_code == status.HTTP_404_NOT_FOUND


# ==========================================
# Testes de CRUD - Create
# ==========================================

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
    
    # Verifica que foi criado no banco
    user = User.objects.get(username="novo_usuario")
    assert user.cpf == "88888888888"
    assert user.cargo.pk == cargo_comum.pk


@pytest.mark.django_db
def test_create_pf_admin_cria_usuario_na_sua_dre(
    api_client, user_pf_admin, cargo_comum, escola_sp
):
    """PF admin pode criar usuários em unidades da sua DRE."""
    api_client.force_authenticate(user=user_pf_admin)
    
    data = {
        "username": "novo_usuario_pf",
        "name": "Novo Usuario PF",
        "email": "novo.pf@example.com",
        "cpf": "88888888889",
        "cargo": cargo_comum.pk,
        "unidades": [escola_sp.codigo_eol],
        "is_app_admin": False,
    }
    
    response = api_client.post("/api/users/gestao-usuarios/", data, format="json")
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["username"] == "novo_usuario_pf"


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


# ==========================================
# Testes de CRUD - Retrieve
# ==========================================

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
    
    assert response.status_code == status.HTTP_404_NOT_FOUND



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
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


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


# ==========================================
# Testes de CRUD - Delete
# ==========================================

@pytest.mark.django_db
def test_delete_gipe_admin_remove_usuario(api_client, user_gipe_admin, usuario_dre_sp):
    """GIPE admin pode deletar usuários."""
    api_client.force_authenticate(user=user_gipe_admin)
    
    response = api_client.delete(f"/api/users/gestao-usuarios/{usuario_dre_sp.uuid}/")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(uuid=usuario_dre_sp.uuid).exists()


# ==========================================
# Testes da action aprovar
# ==========================================

@pytest.mark.django_db
def test_aprovar_gipe_admin_aprova_usuario(
    api_client, user_gipe_admin, usuario_nao_validado
):
    """GIPE admin pode aprovar usuário não validado."""
    assert usuario_nao_validado.is_validado is False
    
    api_client.force_authenticate(user=user_gipe_admin)
    
    response = api_client.post(f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/aprovar/")
    
    assert response.status_code == status.HTTP_200_OK
    
    usuario_nao_validado.refresh_from_db()
    assert usuario_nao_validado.is_validado is True


@pytest.mark.django_db
def test_aprovar_pf_admin_nao_aprova_usuario_de_outra_dre(
    api_client, user_pf_admin, usuario_nao_validado, escola_outra
):
    """PF admin não pode aprovar usuário de outra DRE."""
    # Associa o usuário não validado a escola de outra DRE
    usuario_nao_validado.unidades.clear()
    usuario_nao_validado.unidades.add(escola_outra)
    
    api_client.force_authenticate(user=user_pf_admin)
    
    response = api_client.post(f"/api/users/gestao-usuarios/{usuario_nao_validado.uuid}/aprovar/")
    
    # get_queryset filtra por DRE, então retorna 404
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_aprovar_diretor_nao_pode_aprovar(
    api_client, user_diretor, usuario_nao_validado
):
    """Diretor não pode aprovar usuários (falta permissão CanApproveUser)."""
    # Torna diretor admin para passar CanManageUsers
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
def test_aprovar_ja_validado_continua_validado(
    api_client, user_gipe_admin, usuario_dre_sp
):
    """Aprovar usuário já validado mantém is_validado=True."""
    # Garante que usuario_dre_sp está validado
    usuario_dre_sp.is_validado = True
    usuario_dre_sp.save()
    
    api_client.force_authenticate(user=user_gipe_admin)
    
    response = api_client.post(f"/api/users/gestao-usuarios/{usuario_dre_sp.uuid}/aprovar/")
    
    assert response.status_code == status.HTTP_200_OK
    
    usuario_dre_sp.refresh_from_db()
    assert usuario_dre_sp.is_validado is True
