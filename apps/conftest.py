import secrets
import pytest

from apps.users.tests.factories import UserFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework import status

from apps.users.models import Cargo
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices

User = get_user_model()


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> UserFactory:
    return UserFactory()

# ==================
# Fixtures
# ==================

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_rf():
    return APIRequestFactory()


@pytest.fixture
def cargo_gipe():
    """Cargo GIPE (código 0)."""
    cargo, _ = Cargo.objects.get_or_create(
        codigo=0,
        defaults={"nome": "GIPE"}
    )
    return cargo


@pytest.fixture
def cargo_ponto_focal():
    """Cargo Ponto Focal (código 1)."""
    cargo, _ = Cargo.objects.get_or_create(
        codigo=1,
        defaults={"nome": "Ponto Focal"}
    )
    return cargo


@pytest.fixture
def cargo_diretor():
    """Cargo Diretor (código 3360)."""
    cargo, _ = Cargo.objects.get_or_create(
        codigo=3360,
        defaults={"nome": "Diretor"}
    )
    return cargo


@pytest.fixture
def cargo_comum():
    """Cargo comum (código 9999)."""
    cargo, _ = Cargo.objects.get_or_create(
        codigo=9999,
        defaults={"nome": "Usuário Comum"}
    )
    return cargo


@pytest.fixture
def dre_sp():
    """DRE São Paulo."""
    return Unidade.objects.create(
        codigo_eol="108500",
        nome="DRE São Paulo",
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede="DIRETA",
    )


@pytest.fixture
def dre_outra():
    """DRE em outra localidade."""
    return Unidade.objects.create(
        codigo_eol="999999",
        nome="DRE Outra",
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede="DIRETA",
    )


@pytest.fixture
def escola_sp(dre_sp):
    """Escola vinculada à DRE SP."""
    return Unidade.objects.create(
        codigo_eol="200237",
        nome="EMEI Exemplo SP",
        tipo_unidade=TipoUnidadeChoices.EMEI,
        rede="DIRETA",
        dre=dre_sp,
    )


@pytest.fixture
def escola_outra(dre_outra):
    """Escola vinculada à DRE Outra."""
    return Unidade.objects.create(
        codigo_eol="300000",
        nome="EMEI Outra",
        tipo_unidade=TipoUnidadeChoices.EMEI,
        rede="DIRETA",
        dre=dre_outra,
    )


@pytest.fixture
def user_gipe_admin(cargo_gipe):
    """Usuário GIPE admin."""
    user = User.objects.create_user(
        username="gipe_admin",
        email="gipe.admin@example.com",
        cpf="11111111111",
        cargo=cargo_gipe,
    )
    user.is_app_admin = True
    user.save()
    return user


@pytest.fixture
def user_pf_admin(cargo_ponto_focal, dre_sp):
    """Usuário Ponto Focal admin associado à DRE SP."""
    user = User.objects.create_user(
        username="pf_admin",
        email="pf.admin@example.com",
        cpf="22222222222",
        cargo=cargo_ponto_focal,
    )
    user.is_app_admin = True
    user.save()
    user.unidades.add(dre_sp)
    return user


@pytest.fixture
def user_pf_nao_admin(cargo_ponto_focal, dre_sp):
    """
    Usuário Ponto Focal sem flag de admin (is_app_admin=False).
    """
    pwd = secrets.token_urlsafe(16)
    user = User.objects.create_user(
        username="pf_nao_admin",
        email="pf.na@example.com",
        cpf="33333333333",
        cargo=cargo_ponto_focal,
    )
    user.set_password(pwd)
    user.is_app_admin = False
    user.save()
    user.unidades.add(dre_sp)
    return user


@pytest.fixture
def user_diretor(cargo_diretor, escola_sp):
    """Usuário Diretor (não é admin)."""
    user = User.objects.create_user(
        username="diretor",
        email="diretor@example.com",
        cpf="33333333333",
        cargo=cargo_diretor,
    )
    user.is_app_admin = False
    user.save()
    user.unidades.add(escola_sp)
    return user


@pytest.fixture
def user_comum(cargo_comum, escola_sp):
    """
    Usuário comum (Diretor, professor, etc.), com unidade de escola.
    """
    pwd = secrets.token_urlsafe(16)
    user = User.objects.create_user(
        username="user_comum",
        email="user.comum@example.com",
        cpf="44444444444",
        cargo=cargo_comum,
    )
    user.set_password(pwd)
    user.is_app_admin = False
    user.save()
    user.unidades.add(escola_sp)
    return user


@pytest.fixture
def outro_user_comum(cargo_comum, escola_outra):
    """
    Outro usuário comum, em outra DRE.
    """
    pwd = secrets.token_urlsafe(16)
    user = User.objects.create_user(
        username="outro_user",
        email="outro@example.com",
        cpf="55555555555",
        cargo=cargo_comum,
    )
    user.set_password(pwd)
    user.is_app_admin = False
    user.save()
    user.unidades.add(escola_outra)
    return user


@pytest.fixture
def usuario_nao_validado(cargo_comum, escola_sp):
    """Usuário comum não validado."""
    user = User.objects.create_user(
        username="nao_validado",
        email="naovalidado@example.com",
        cpf="55555555555",
        cargo=cargo_comum,
        is_validado=False,
    )
    user.unidades.add(escola_sp)
    return user


@pytest.fixture
def usuario_dre_sp(cargo_comum, dre_sp):
    """Usuário associado à DRE SP."""
    user = User.objects.create_user(
        username="usuario_dre_sp",
        email="usuario.dre.sp@example.com",
        cpf="66666666666",
        cargo=cargo_comum,
    )
    user.unidades.add(dre_sp)
    return user


@pytest.fixture
def usuario_dre_outra(cargo_comum, dre_outra):
    """Usuário associado à DRE Outra."""
    user = User.objects.create_user(
        username="usuario_dre_outra",
        email="usuario.dre.outra@example.com",
        cpf="77777777777",
        cargo=cargo_comum,
    )
    user.unidades.add(dre_outra)
    return user



