import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from apps.users.models import Cargo

from apps.users.api.serializers.gestao_usuario_serializer import (
    GestaoUsuarioSerializer,
    GestaoUsuarioListaSerializer,
    GestaoUsuarioRetrieveSerializer,
    format_cpf,
)
from apps.unidades.models.unidades import TipoGestaoChoices

User = get_user_model()


# ==========================================
# Testes utilitário format_cpf
# ==========================================

def test_format_cpf_retorna_vazio_para_entrada_vazia():
    assert format_cpf("") == ""
    


def test_format_cpf_retorna_original_quando_nao_tem_11_digitos():
    assert format_cpf("1234567890") == "1234567890"
    assert format_cpf("ABC123") == "ABC123"


def test_format_cpf_formata_para_padroes_com_pontos_e_traco():
    assert format_cpf("12345678901") == "123.456.789-01"
    assert format_cpf("123.456.789-01") == "123.456.789-01"


# ==========================================
# Testes GestaoUsuarioListaSerializer - rf_ou_cpf e rede
# ==========================================

@pytest.mark.django_db
def test_lista_serializer_get_rf_ou_cpf_prefere_cpf_formatado(user_comum):
    serializer = GestaoUsuarioListaSerializer()
    resultado = serializer.get_rf_ou_cpf(user_comum)
    assert resultado == format_cpf(user_comum.cpf)


def test_lista_serializer_get_rf_ou_cpf_retorna_username_quando_sem_cpf():
    usuario = SimpleNamespace(cpf="", username="rf123")
    serializer = GestaoUsuarioListaSerializer()

    assert serializer.get_rf_ou_cpf(usuario) == "rf123"


def test_lista_serializer_get_rede_usa_display_quando_disponivel():
    usuario = SimpleNamespace(
        get_rede_display=lambda: "Rede Direta",
        rede="IGNORADO",
    )
    serializer = GestaoUsuarioListaSerializer()

    assert serializer.get_rede(usuario) == "Rede Direta"


def test_lista_serializer_get_rede_fallback_para_valor_bruto_quando_display_falha():
    def boom():
        raise AttributeError("boom")

    usuario = SimpleNamespace(
        get_rede_display=boom,
        rede="INDIRETA",
    )
    serializer = GestaoUsuarioListaSerializer()

    assert serializer.get_rede(usuario) == "INDIRETA"


def test_lista_serializer_get_rede_retorna_hifen_quando_nao_ha_label():
    def boom():
        raise AttributeError("boom")

    usuario = SimpleNamespace(
        get_rede_display=boom,
        rede="",
    )
    serializer = GestaoUsuarioListaSerializer()

    assert serializer.get_rede(usuario) == "-"


# ==========================================
# Testes para validate_unidades
# ==========================================

@pytest.mark.django_db
def test_validate_unidades_user_nao_admin_negado(api_rf, user_comum, escola_sp):
    """Usuário sem is_app_admin não pode definir unidades."""
    request = api_rf.post("/fake/")
    request.user = user_comum
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    with pytest.raises(serializers.ValidationError, match="não tem permissão para definir unidades"):
        serializer.validate_unidades([escola_sp])


@pytest.mark.django_db
def test_validate_unidades_diretor_nao_admin_negado(api_rf, user_diretor, escola_sp):
    """Diretor sem is_app_admin não pode definir unidades."""
    request = api_rf.post("/fake/")
    request.user = user_diretor
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    with pytest.raises(serializers.ValidationError, match="não tem permissão para definir unidades"):
        serializer.validate_unidades([escola_sp])


@pytest.mark.django_db
def test_validate_unidades_admin_nao_gipe_nao_pf_negado(api_rf, cargo_comum, escola_sp):
    """Usuário admin que não é GIPE nem PF não pode definir unidades."""
    # Criar um usuário admin mas sem cargo GIPE ou PF
    user_admin_comum = User.objects.create_user(
        username="admin_comum",
        email="admin.comum@example.com",
        cpf="98989898989",
        cargo=cargo_comum,
    )
    user_admin_comum.is_app_admin = True
    user_admin_comum.save()
    
    request = api_rf.post("/fake/")
    request.user = user_admin_comum
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    with pytest.raises(serializers.ValidationError, match="não tem permissão para definir unidades"):
        serializer.validate_unidades([escola_sp])


@pytest.mark.django_db
def test_validate_unidades_gipe_admin_permite_qualquer_unidade(
    api_rf, user_gipe_admin, escola_sp, escola_outra
):
    """GIPE admin pode definir qualquer unidade."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    # Não deve lançar exceção
    result = serializer.validate_unidades([escola_sp, escola_outra])
    assert result == [escola_sp, escola_outra]


@pytest.mark.django_db
def test_validate_unidades_pf_admin_permite_apenas_propria_dre(
    api_rf, user_pf_admin, escola_sp, dre_sp
):
    """PF admin pode definir unidades apenas da própria DRE."""
    request = api_rf.post("/fake/")
    request.user = user_pf_admin
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    # escola_sp pertence a dre_sp, que está nas unidades do user_pf_admin
    result = serializer.validate_unidades([escola_sp])
    assert result == [escola_sp]


@pytest.mark.django_db
def test_validate_unidades_pf_admin_nega_outra_dre(
    api_rf, user_pf_admin, escola_outra
):
    """PF admin não pode definir unidades de outra DRE."""
    request = api_rf.post("/fake/")
    request.user = user_pf_admin
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    with pytest.raises(serializers.ValidationError, match="só pode cadastrar usuários para unidades de sua DRE"):
        serializer.validate_unidades([escola_outra])


# ==========================================
# Testes para validate_is_app_admin
# ==========================================

@pytest.mark.django_db
def test_validate_is_app_admin_gipe_pode_atribuir(api_rf, user_gipe_admin):
    """GIPE pode marcar is_app_admin=True."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    result = serializer.validate_is_app_admin(True)
    assert result is True


@pytest.mark.django_db
def test_validate_is_app_admin_pf_nao_pode_atribuir(api_rf, user_pf_admin):
    """PF não pode marcar is_app_admin=True."""
    request = api_rf.post("/fake/")
    request.user = user_pf_admin
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    with pytest.raises(serializers.ValidationError, match="Somente usuários com perfil GIPE"):
        serializer.validate_is_app_admin(True)


@pytest.mark.django_db
def test_is_valid_formata_erro_com_detail(api_rf, user_gipe_admin, cargo_comum):
    """Quando há erro de validação, is_valid retorna formato específico."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    # Dados inválidos: faltando campo obrigatório 'cpf'
    data = {
        "username": "teste",
        "name": "Teste",
        "email": "teste@example.com",
        # cpf ausente
        "cargo": cargo_comum.pk,
        "rede": "DIRETA",
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    
    assert serializer.is_valid(raise_exception=False) is False
    assert "detail" in serializer.errors


@pytest.mark.django_db
def test_is_valid_levanta_excecao_quando_raise_exception_true(
    api_rf, user_gipe_admin, cargo_comum
):
    """Quando raise_exception=True, levanta ValidationError."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "teste",
        "name": "Teste",
        # cpf ausente
        "cargo": cargo_comum.pk,
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
def test_is_valid_preserva_detail_se_ja_existe(api_rf, user_gipe_admin):
    """
    Se _errors já tem 'detail', is_valid não sobrescreve com novo dict,
    apenas não executa o código de formatação. Cobre linha 89.
    """
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    # Cria serializer inválido
    serializer = GestaoUsuarioSerializer(data={}, context={"request": request})
    
    # Força a validação primeiro para popular _errors
    serializer.is_valid(raise_exception=False)
    
    # Agora simula que _errors já tem 'detail' (como se fosse uma validação anterior)
    serializer._errors = {"detail": "Erro customizado que já estava lá"}
    
    # Chama is_valid novamente - deve preservar o 'detail' customizado
    # porque a linha 89 só executa se 'detail' NÃO estiver em _errors
    result = serializer.is_valid(raise_exception=False)
    
    assert result is False
    # O erro customizado deve ser preservado
    assert serializer.errors.get("detail") == "Erro customizado que já estava lá"


@pytest.mark.django_db
def test_create_pf_admin_cria_usuario_sem_is_app_admin_mesmo_se_payload(
    api_rf, user_pf_admin, cargo_comum, escola_sp
):
    """PF admin não consegue criar usuário com is_app_admin=True mesmo enviando no payload."""
    request = api_rf.post("/fake/")
    request.user = user_pf_admin
    
    data = {
        "username": "novo_user",
        "name": "Novo User",
        "email": "novo.user@example.com",
        "cpf": "88888888888",
        "cargo": cargo_comum.pk,
        "rede": "DIRETA",
        "unidades": [escola_sp.pk],
        "is_app_admin": True,  # PF tentando forçar
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    
    # validate_is_app_admin deve bloquear isso
    assert serializer.is_valid(raise_exception=False) is False

@pytest.mark.django_db
def test_update_gipe_pode_mudar_is_app_admin(
    api_rf, user_gipe_admin, user_comum
):
    """GIPE admin pode alterar is_app_admin de outro usuário."""
    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin
    
    assert user_comum.is_app_admin is False
    
    data = {"is_app_admin": True}
    
    serializer = GestaoUsuarioSerializer(
        user_comum, 
        data=data, 
        partial=True,
        context={"request": request}
    )
    assert serializer.is_valid(raise_exception=True)
    
    updated_user = serializer.save()
    assert updated_user.is_app_admin is True


@pytest.mark.django_db
def test_update_pf_nao_pode_mudar_is_app_admin(
    api_rf, user_pf_admin, user_comum
):
    """PF admin tentando alterar is_app_admin=True falha na validação."""
    request = api_rf.patch("/fake/")
    request.user = user_pf_admin
    
    assert user_comum.is_app_admin is False
    
    data = {"is_app_admin": True}
    
    serializer = GestaoUsuarioSerializer(
        user_comum,
        data=data,
        partial=True,
        context={"request": request}
    )
    
    # Deve falhar na validação porque PF não pode setar is_app_admin=True
    assert serializer.is_valid(raise_exception=False) is False
    assert "detail" in serializer.errors

@pytest.mark.django_db
def test_update_pode_alterar_unidades(
    api_rf, user_gipe_admin, user_comum, escola_sp, escola_outra
):
    """Update pode alterar as unidades do usuário."""
    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin
    
    # user_comum inicialmente tem escola_sp
    assert escola_sp in user_comum.unidades.all()
    
    data = {"unidades": [escola_outra.pk]}
    
    serializer = GestaoUsuarioSerializer(
        user_comum,
        data=data,
        partial=True,
        context={"request": request}
    )
    assert serializer.is_valid(raise_exception=True)
    
    updated_user = serializer.save()
    assert escola_outra in updated_user.unidades.all()
    assert escola_sp not in updated_user.unidades.all()


@pytest.mark.django_db
def test_update_unidades_none_nao_altera(
    api_rf, user_gipe_admin, user_comum, escola_sp
):
    """Se unidades não for enviado no update, não altera as unidades existentes."""
    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin
    
    # user_comum inicialmente tem escola_sp
    assert escola_sp in user_comum.unidades.all()
    
    data = {"name": "Nome Mudado"}  # sem campo unidades
    
    serializer = GestaoUsuarioSerializer(
        user_comum,
        data=data,
        partial=True,
        context={"request": request}
    )
    assert serializer.is_valid(raise_exception=True)
    
    updated_user = serializer.save()
    # unidades devem permanecer as mesmas
    assert escola_sp in updated_user.unidades.all()


@pytest.mark.django_db
def test_update_is_app_admin_none_nao_altera(
    api_rf, user_gipe_admin, user_comum
):
    """Se is_app_admin não for enviado no update, não altera o valor existente."""
    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin
    
    user_comum.is_app_admin = True
    user_comum.save()
    
    data = {"name": "Nome Mudado"}  # sem campo is_app_admin
    
    serializer = GestaoUsuarioSerializer(
        user_comum,
        data=data,
        partial=True,
        context={"request": request}
    )
    assert serializer.is_valid(raise_exception=True)
    
    updated_user = serializer.save()
    # is_app_admin deve permanecer True
    assert updated_user.is_app_admin is True


@pytest.mark.django_db
def test_update_pf_validacao_unidades_respeitada(
    api_rf, user_pf_admin, user_comum, escola_outra
):
    """PF tentando atualizar unidades para DRE não permitida deve falhar na validação."""
    request = api_rf.patch("/fake/")
    request.user = user_pf_admin
    
    data = {"unidades": [escola_outra.pk]}  # escola_outra não está na DRE do PF
    
    serializer = GestaoUsuarioSerializer(
        user_comum,
        data=data,
        partial=True,
        context={"request": request}
    )
    
    # Deve falhar na validação
    assert serializer.is_valid(raise_exception=False) is False

@pytest.mark.django_db
def test_retrieve_serializer_retorna_is_active(user_comum):
    serializer = GestaoUsuarioRetrieveSerializer(user_comum)
    data = serializer.data

    assert data["is_active"] == user_comum.is_active


@pytest.mark.django_db
def test_retrieve_serializer_retorna_codigo_eol_unidade_e_dre(
    user_comum,
    escola_sp,
    dre_sp,
):
    escola_sp.dre = dre_sp
    escola_sp.save()

    user_comum.unidades.clear()
    user_comum.unidades.add(escola_sp)

    serializer = GestaoUsuarioRetrieveSerializer(user_comum)
    data = serializer.data

    assert data["codigo_eol_unidade"] == escola_sp.codigo_eol
    assert data["codigo_eol_dre_da_unidade"] == escola_sp.dre_id


@pytest.mark.django_db
def test_retrieve_serializer_retorna_unidade_sem_dre(
    user_comum,
    escola_sp,
):
    """
    Usuário com unidade associada, mas sem DRE.
    """
    escola_sp.dre = None
    escola_sp.save()

    user_comum.unidades.add(escola_sp)

    serializer = GestaoUsuarioRetrieveSerializer(user_comum)
    data = serializer.data

    assert data["codigo_eol_unidade"] == escola_sp.codigo_eol
    assert data["codigo_eol_dre_da_unidade"] is None


@pytest.mark.django_db
def test_retrieve_serializer_retorna_none_quando_usuario_sem_unidade(cargo_comum):
    user = User.objects.create_user(
        username="sem_unidade",
        cpf="12345678901",
        cargo=cargo_comum,
    )

    serializer = GestaoUsuarioRetrieveSerializer(user)
    data = serializer.data

    assert data["codigo_eol_unidade"] is None
    assert data["codigo_eol_dre_da_unidade"] is None


@pytest.mark.django_db
class TestGestaoUsuarioRetrieveSerializer:

    def test_data_inativacao_formatada(self):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")

        data_inativacao = timezone.localtime(
            timezone.datetime(2026, 1, 13, 14, 29, tzinfo=timezone.get_current_timezone())
        )

        usuario = User.objects.create(
            username="1234567",
            cpf="12345678901",
            name="Usuário Teste",
            cargo=cargo,
            is_active=False,
            data_inativacao=data_inativacao,
        )

        serializer = GestaoUsuarioRetrieveSerializer(usuario)

        assert serializer.data["data_inativacao_formatada"] == "13/01/2026 às 14:29h."
    
    def test_responsavel_inativacao_nome(self):

        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")

        responsavel = User.objects.create(
            username="1234567",
            cpf="99988877766",
            name="Administrador Responsável",
            cargo=cargo,
            is_active=True,
        )

        usuario = User.objects.create(
            username="usuario_inativado",
            cpf="12345678901",
            name="Usuário Inativado",
            cargo=cargo,
            is_active=False,
            responsavel_inativacao=responsavel.username,
        )

        serializer = GestaoUsuarioRetrieveSerializer(usuario)

        assert serializer.data["responsavel_inativacao_nome"] == "Administrador Responsável"
    
    def test_responsavel_inativacao_nome_quando_usuario_nao_existe(self):
        cargo = Cargo.objects.create(codigo=1234, nome="Cargo Teste")

        usuario = User.objects.create(
            username="usuario_inativado",
            cpf="12345678901",
            name="Usuário Inativado",
            cargo=cargo,
            is_active=False,
            responsavel_inativacao="1234568",
        )

        serializer = GestaoUsuarioRetrieveSerializer(usuario)

        assert serializer.data["responsavel_inativacao_nome"] is None

@pytest.mark.django_db
def test_validate_cpf_invalido(api_rf, user_gipe_admin):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(context={"request": request})

    with pytest.raises(serializers.ValidationError, match="CPF informado é inválido"):
        serializer.validate_cpf("111.111.111-11")

@pytest.mark.django_db
def test_validate_cpf_duplicado(api_rf, user_gipe_admin, cargo_comum):
    User.objects.create_user(
        username="usercpf",
        email="user@sme.prefeitura.sp.gov.br",
        cpf="52998224725",
        cargo=cargo_comum,
    )

    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(context={"request": request})

    with pytest.raises(serializers.ValidationError, match="Já existe um usuário"):
        serializer.validate_cpf("529.982.247-25")

@pytest.mark.django_db
def test_validate_cpf_valido(api_rf, user_gipe_admin):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(context={"request": request})

    cpf = "52998224725"
    result = serializer.validate_cpf(cpf)

    assert result == cpf

@pytest.mark.django_db
def test_validate_cpf_update_mesmo_usuario(api_rf, cargo_comum):
    user = User.objects.create_user(
        username="userupdate",
        email="userupdate@sme.prefeitura.sp.gov.br",
        cpf="52998224725",
        cargo=cargo_comum,
    )

    request = api_rf.post("/fake/")
    request.user = user

    serializer = GestaoUsuarioSerializer(
        instance=user,
        context={"request": request}
    )

    result = serializer.validate_cpf("529.982.247-25")

    assert result == "52998224725"

@pytest.mark.django_db
def test_validate_email_duplicado(api_rf, user_gipe_admin, user_comum):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(context={"request": request})

    with pytest.raises(serializers.ValidationError, match="já está cadastrado"):
        serializer.validate_email(user_comum.email)

@pytest.mark.django_db
def test_validate_email_nao_institucional(api_rf, user_gipe_admin):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(context={"request": request})

    with pytest.raises(serializers.ValidationError, match="e-mail institucional"):
        serializer.validate_email("teste@gmail.com")

@pytest.mark.django_db
def test_validate_email_valido(api_rf, user_gipe_admin):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(context={"request": request})

    email = "teste@sme.prefeitura.sp.gov.br"

    result = serializer.validate_email(email)

    assert result == email

@pytest.mark.django_db
def test_pf_nao_pode_cadastrar_dre_fora(api_rf, user_pf_admin, dre_outra):
    serializer = GestaoUsuarioSerializer()

    with pytest.raises(serializers.ValidationError):
        serializer._validate_ponto_focal_unidades(
            user_pf_admin,
            [dre_outra]
        )

@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.SmeIntegracaoService.usuario_core_sso_or_none")
def test_validate_core_sso_sucesso(mock_service, api_rf, user_gipe_admin):
    mock_service.return_value = True

    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    attrs = {
        "username": "1234567",
        "rede": TipoGestaoChoices.DIRETA,
    }

    result = serializer.validate(attrs)

    assert result == attrs

@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.SmeIntegracaoService.usuario_core_sso_or_none")
def test_validate_core_sso_nao_encontrado(mock_service, api_rf, user_gipe_admin):
    mock_service.return_value = None

    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    attrs = {
        "username": "1234567",
        "rede": TipoGestaoChoices.DIRETA,
    }

    with pytest.raises(serializers.ValidationError, match="verifique se o código"):
        serializer.validate(attrs)

@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.SmeIntegracaoService.usuario_core_sso_or_none")
def test_validate_core_sso_erro(mock_service, api_rf, user_gipe_admin):
    mock_service.side_effect = Exception("Erro")

    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    attrs = {
        "username": "1234567",
        "rede": TipoGestaoChoices.DIRETA,
    }

    with pytest.raises(serializers.ValidationError, match="Não foi possível validar"):
        serializer.validate(attrs)

@pytest.mark.django_db
def test_validate_indireta_nao_chama_core(api_rf, user_gipe_admin):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    attrs = {
        "username": "1234567",
        "rede": TipoGestaoChoices.INDIRETA,
    }

    result = serializer.validate(attrs)

    assert result == attrs

@pytest.mark.django_db
def test_create_usuario_gipe(api_rf, user_gipe_admin, cargo_comum, escola_sp):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    data = {
        "username": "novo1234",
        "name": "Novo",
        "email": "novo@sme.prefeitura.sp.gov.br",
        "cpf": "52998224725",
        "cargo": cargo_comum,
        "rede": TipoGestaoChoices.DIRETA,
        "unidades": [escola_sp],
        "is_app_admin": True,
    }

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    user = serializer.create(data)

    assert user.pk
    assert user.is_app_admin is True

@pytest.mark.django_db
def test_create_usuario_pf_nao_admin(api_rf, user_pf_admin, cargo_comum, escola_sp):
    request = api_rf.post("/fake/")
    request.user = user_pf_admin

    data = {
        "username": "novo1235",
        "name": "Novo",
        "email": "novo@sme.prefeitura.sp.gov.br",
        "cpf": "98765432100",
        "cargo": cargo_comum,
        "rede": TipoGestaoChoices.DIRETA,
        "unidades": [escola_sp],
        "is_app_admin": True,
    }

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    user = serializer.create(data)

    assert user.is_app_admin is False

@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_create_indireta_chama_core_sso(
    mock_core, api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    data = {
        "username": "novo9999",
        "name": "Novo",
        "email": "novo@sme.prefeitura.sp.gov.br",
        "cpf": "12312312312",
        "cargo": cargo_comum,
        "rede": TipoGestaoChoices.INDIRETA,
        "unidades": [escola_sp],
    }

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    serializer.create(data)

    mock_core.assert_called_once()

@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.User.objects.create_user")
def test_create_erro_dispara_validation_error(
    mock_create, api_rf, user_gipe_admin
):
    mock_create.side_effect = Exception("Erro banco")

    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    serializer = GestaoUsuarioSerializer(
        context={"request": request}
    )

    data = {
        "username": "xpto123",
        "email": "xpto@sme.prefeitura.sp.gov.br",
        "cpf": "12345678912",
        "rede": TipoGestaoChoices.DIRETA,
    }

    with pytest.raises(serializers.ValidationError, match="Erro ao criar usuário"):
        serializer.create(data)

@pytest.mark.django_db
def test_validate_email_update_mesmo_usuario_nao_gera_erro(
    api_rf, cargo_comum
):
    user = User.objects.create_user(
        username="useremail",
        email="useremail@sme.prefeitura.sp.gov.br",
        cpf="52998224725",
        cargo=cargo_comum,
    )

    request = api_rf.patch("/fake/")
    request.user = user

    serializer = GestaoUsuarioSerializer(
        instance=user,
        context={"request": request}
    )

    result = serializer.validate_email(
        "useremail@sme.prefeitura.sp.gov.br"
    )

    assert result == "useremail@sme.prefeitura.sp.gov.br"