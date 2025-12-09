import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from apps.users.permissions import CanManageUsers, CanApproveUser

User = get_user_model()


class DummyView:
    """
    View fake só para podermos controlar o atributo .action
    que o DRF preenche em ViewSets.
    """
    def __init__(self, action):
        self.action = action


# =========================
# Tests para CanManageUsers
# =========================

@pytest.mark.django_db
def test_can_manage_users_anonymous(api_rf):
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = AnonymousUser()

    view = DummyView(action="list")

    assert perm.has_permission(request, view) is False


@pytest.mark.django_db
def test_can_manage_users_gipe_admin_qualquer_acao(api_rf, user_gipe_admin):
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_gipe_admin

    for action in ["list", "retrieve", "create", "update", "partial_update", "destroy"]:
        view = DummyView(action=action)
        assert perm.has_permission(request, view) is True


@pytest.mark.django_db
def test_can_manage_users_pf_admin_acoes_permitidas(api_rf, user_pf_admin):
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_pf_admin

    # Ações permitidas para PF admin
    for action in ["list", "retrieve", "create", "update", "partial_update"]:
        view = DummyView(action=action)
        assert perm.has_permission(request, view) is True

    # Ex: destroy não permitido
    view = DummyView(action="destroy")
    assert perm.has_permission(request, view) is False


@pytest.mark.django_db
def test_can_manage_users_nao_admin_so_retrieve_update(api_rf, user_comum):
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_comum

    # list / create -> não pode
    for action in ["list", "create", "destroy"]:
        view = DummyView(action=action)
        assert perm.has_permission(request, view) is False

    # retrieve / update / partial_update -> pode (mas only próprio registro no has_object_permission)
    for action in ["retrieve", "update", "partial_update"]:
        view = DummyView(action=action)
        assert perm.has_permission(request, view) is True


# ===================================
# Tests para has_object_permission de CanManageUsers
# ===================================

@pytest.mark.django_db
def test_can_manage_users_object_gipe_admin_acessa_qualquer_usuario(api_rf, user_gipe_admin, user_comum):
    """GIPE admin pode acessar qualquer usuário."""
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_gipe_admin
    view = DummyView(action="retrieve")

    assert perm.has_object_permission(request, view, user_comum) is True


@pytest.mark.django_db
def test_can_manage_users_object_pf_admin_acessa_usuario_mesma_dre(
    api_rf, user_pf_admin, user_comum, dre_sp, escola_sp
):
    """PF admin pode acessar usuário com unidade na mesma DRE."""
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_pf_admin
    view = DummyView(action="retrieve")

    # user_comum tem escola_sp que pertence a dre_sp
    # user_pf_admin tem dre_sp nas unidades
    assert perm.has_object_permission(request, view, user_comum) is True


@pytest.mark.django_db
def test_can_manage_users_object_pf_admin_nao_acessa_usuario_outra_dre(
    api_rf, user_pf_admin, outro_user_comum
):
    """PF admin não pode acessar usuário de outra DRE."""
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_pf_admin
    view = DummyView(action="retrieve")

    # outro_user_comum está em escola_outra, que pertence a dre_outra
    # user_pf_admin só tem acesso a dre_sp
    assert perm.has_object_permission(request, view, outro_user_comum) is False


@pytest.mark.django_db
def test_can_manage_users_object_usuario_comum_acessa_proprio_registro(api_rf, user_comum):
    """Usuário não-admin pode acessar apenas seu próprio registro."""
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_comum
    view = DummyView(action="retrieve")

    assert perm.has_object_permission(request, view, user_comum) is True


@pytest.mark.django_db
def test_can_manage_users_object_usuario_comum_nao_acessa_outro_usuario(
    api_rf, user_comum, outro_user_comum
):
    """Usuário não-admin não pode acessar registro de outro usuário."""
    perm = CanManageUsers()
    request = api_rf.get("/fake-url/")
    request.user = user_comum
    view = DummyView(action="retrieve")

    assert perm.has_object_permission(request, view, outro_user_comum) is False


# ===========================
# Tests para CanApproveUser
# ===========================

@pytest.mark.django_db
def test_can_approve_user_anonymous_negado(api_rf):
    """Usuário anônimo não pode aprovar."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = AnonymousUser()
    view = DummyView(action="approve")

    assert perm.has_permission(request, view) is False


@pytest.mark.django_db
def test_can_approve_user_gipe_admin_permitido(api_rf, user_gipe_admin):
    """GIPE admin pode aprovar usuários."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_gipe_admin
    view = DummyView(action="approve")

    assert perm.has_permission(request, view) is True


@pytest.mark.django_db
def test_can_approve_user_pf_admin_permitido(api_rf, user_pf_admin):
    """PF admin pode aprovar usuários."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_pf_admin
    view = DummyView(action="approve")

    # Verifica explicitamente que is_ponto_focal é True
    assert user_pf_admin.is_ponto_focal is True
    assert perm.has_permission(request, view) is True


@pytest.mark.django_db
def test_can_approve_user_pf_nao_admin_negado(api_rf, user_pf_nao_admin):
    """PF sem is_app_admin não pode aprovar."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_pf_nao_admin
    view = DummyView(action="approve")

    assert perm.has_permission(request, view) is False


@pytest.mark.django_db
def test_can_approve_user_comum_negado(api_rf, user_comum):
    """Usuário comum não pode aprovar."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_comum
    view = DummyView(action="approve")

    assert perm.has_permission(request, view) is False


# =====================================================
# Tests para has_object_permission de CanApproveUser
# =====================================================

@pytest.mark.django_db
def test_can_approve_user_object_gipe_admin_aprova_qualquer_um(
    api_rf, user_gipe_admin, user_comum
):
    """GIPE admin pode aprovar qualquer usuário."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_gipe_admin
    view = DummyView(action="approve")

    assert perm.has_object_permission(request, view, user_comum) is True


@pytest.mark.django_db
def test_can_approve_user_object_pf_admin_aprova_usuario_mesma_dre(
    api_rf, user_pf_admin, user_comum
):
    """PF admin pode aprovar usuário com unidade na mesma DRE."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_pf_admin
    view = DummyView(action="approve")

    # user_comum tem escola_sp que pertence a dre_sp
    # user_pf_admin tem dre_sp nas unidades
    assert perm.has_object_permission(request, view, user_comum) is True


@pytest.mark.django_db
def test_can_approve_user_object_pf_admin_nao_aprova_usuario_outra_dre(
    api_rf, user_pf_admin, outro_user_comum
):
    """PF admin não pode aprovar usuário de outra DRE."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_pf_admin
    view = DummyView(action="approve")

    # outro_user_comum está em escola_outra, que pertence a dre_outra
    assert perm.has_object_permission(request, view, outro_user_comum) is False


@pytest.mark.django_db
def test_can_approve_user_object_usuario_comum_nao_pode_aprovar(
    api_rf, user_comum, outro_user_comum
):
    """Usuário comum não pode aprovar ninguém."""
    perm = CanApproveUser()
    request = api_rf.post("/fake-url/")
    request.user = user_comum
    view = DummyView(action="approve")

    assert perm.has_object_permission(request, view, outro_user_comum) is False
