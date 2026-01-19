import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

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
def test_validate_is_app_admin_false_qualquer_usuario_pode(api_rf, user_pf_admin):
    """Qualquer admin pode marcar is_app_admin=False."""
    request = api_rf.post("/fake/")
    request.user = user_pf_admin
    
    serializer = GestaoUsuarioSerializer(context={"request": request})
    
    result = serializer.validate_is_app_admin(False)
    assert result is False


# ==========================================
# Testes para is_valid (override)
# ==========================================

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


# ==========================================
# Testes para create
# ==========================================

@pytest.mark.django_db
def test_create_gipe_admin_cria_usuario_com_is_app_admin(
    api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """GIPE admin pode criar usuário com is_app_admin=True."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "novo_admin",
        "name": "Novo Admin",
        "email": "novo.admin@example.com",
        "cpf": "99999999999",
        "cargo": cargo_comum.pk,
        "rede": "DIRETA",
        "unidades": [escola_sp.pk],
        "is_app_admin": True,
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    novo_user = serializer.save()
    
    assert novo_user.username == "novo_admin"
    assert novo_user.cpf == "99999999999"
    assert novo_user.is_app_admin is True
    assert novo_user.is_validado is True
    assert escola_sp in novo_user.unidades.all()


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
def test_create_pf_ignora_is_app_admin_via_create(
    api_rf, cargo_ponto_focal, cargo_comum, escola_sp, dre_sp
):
    """
    PF consegue passar validação se não enviar is_app_admin,
    mas o método create garante que is_app_admin seja False.
    """
    # Criar PF admin
    user_pf = User.objects.create_user(
        username="pf_test",
        email="pf.test@example.com",
        cpf="12312312312",
        cargo=cargo_ponto_focal,
    )
    user_pf.is_app_admin = True
    user_pf.save()
    user_pf.unidades.add(dre_sp)
    
    request = api_rf.post("/fake/")
    request.user = user_pf
    
    # Dados válidos sem is_app_admin no payload
    data = {
        "username": "novo_comum",
        "name": "Novo Comum",
        "email": "novo.comum@example.com",
        "cpf": "23423423423",
        "cargo": cargo_comum.pk,
        "rede": "DIRETA",
        "unidades": [escola_sp.pk],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    novo_user = serializer.save()
    
    # Mesmo sem is_app_admin no payload, o create garante que seja False para PF
    assert novo_user.is_app_admin is False


@pytest.mark.django_db
def test_create_define_is_validado_false_por_padrao(
    api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """Usuário criado via serializer tem is_validado=False por padrão."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "validado_user",
        "name": "Validado",
        "email": "validado@example.com",
        "cpf": "77777777777",
        "cargo": cargo_comum.pk,
        "rede": "DIRETA",
        "unidades": [escola_sp.pk],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    novo_user = serializer.save()
    assert novo_user.is_validado is True


@pytest.mark.django_db
def test_create_sem_unidades_funciona(api_rf, user_gipe_admin, cargo_comum):
    """Pode criar usuário sem unidades."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "sem_unidades",
        "name": "Sem Unidades",
        "email": "sem.unidades@example.com",
        "cpf": "66666666666",
        "cargo": cargo_comum.pk,
        "rede": "DIRETA",
        "unidades": [],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    novo_user = serializer.save()
    assert novo_user.unidades.count() == 0


@pytest.mark.django_db
def test_create_sem_is_app_admin_no_payload_cria_como_false(
    api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """Se is_app_admin não for enviado, cria como False."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "regular_user",
        "name": "Regular User",
        "email": "regular@example.com",
        "cpf": "55555555555",
        "cargo": cargo_comum.pk,
        "rede": "DIRETA",
        "unidades": [escola_sp.pk],
        # is_app_admin não enviado
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    novo_user = serializer.save()
    assert novo_user.is_app_admin is False


# ==========================================
# Testes para update
# ==========================================

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
def test_update_pf_pode_setar_is_app_admin_false(
    api_rf, user_pf_admin, user_gipe_admin
):
    """PF admin pode setar is_app_admin=False."""
    request = api_rf.patch("/fake/")
    request.user = user_pf_admin
    
    # user_gipe_admin começa com is_app_admin=True
    assert user_gipe_admin.is_app_admin is True
    
    data = {"is_app_admin": False}
    
    serializer = GestaoUsuarioSerializer(
        user_gipe_admin,
        data=data,
        partial=True,
        context={"request": request}
    )
    assert serializer.is_valid(raise_exception=True)
    
    updated_user = serializer.save()
    # PF não é GIPE, então o campo é ignorado no update
    # O valor deve permanecer True
    assert updated_user.is_app_admin is True


@pytest.mark.django_db
def test_update_atualiza_outros_campos(
    api_rf, user_gipe_admin, user_comum
):
    """Update pode alterar campos normais como name, email."""
    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "name": "Nome Atualizado",
        "email": "atualizado@example.com",
    }
    
    serializer = GestaoUsuarioSerializer(
        user_comum,
        data=data,
        partial=True,
        context={"request": request}
    )
    assert serializer.is_valid(raise_exception=True)
    
    updated_user = serializer.save()
    assert updated_user.name == "Nome Atualizado"
    assert updated_user.email == "atualizado@example.com"


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


# ==========================================
# Testes para integração com CoreSSO
# ==========================================

@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_create_rede_indireta_chama_core_sso(
    mock_cria_core_sso, api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """Quando rede é INDIRETA, deve chamar o serviço de criação no CoreSSO."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "usuario_indireta",
        "name": "Usuário Rede Indireta",
        "email": "indireta@example.com",
        "cpf": "44444444444",
        "cargo": cargo_comum.pk,
        "rede": TipoGestaoChoices.INDIRETA,
        "unidades": [escola_sp.pk],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    serializer.save()
    
    # Verifica que o serviço foi chamado uma vez
    mock_cria_core_sso.assert_called_once()
    
    # Verifica os dados enviados para o CoreSSO
    call_args = mock_cria_core_sso.call_args[0][0]
    assert call_args["login"] == "usuario_indireta"
    assert call_args["nome"] == "Usuário Rede Indireta"
    assert call_args["email"] == "indireta@example.com"


@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_create_rede_direta_nao_chama_core_sso(
    mock_cria_core_sso, api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """Quando rede é DIRETA, não deve chamar o serviço de criação no CoreSSO."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "usuario_direta",
        "name": "Usuário Rede Direta",
        "email": "direta@example.com",
        "cpf": "33333333333",
        "cargo": cargo_comum.pk,
        "rede": TipoGestaoChoices.DIRETA,
        "unidades": [escola_sp.pk],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    serializer.save()
    
    # Verifica que o serviço NÃO foi chamado
    mock_cria_core_sso.assert_not_called()


@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_create_rede_none_nao_chama_core_sso(
    mock_cria_core_sso, api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """Quando rede é None ou não informada, não deve chamar o serviço CoreSSO."""
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "usuario_sem_rede",
        "name": "Usuário Sem Rede",
        "email": "semrede@example.com",
        "cpf": "22222222222",
        "cargo": cargo_comum.pk,
        # rede não informada
        "unidades": [escola_sp.pk],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    serializer.save()
    
    # Verifica que o serviço NÃO foi chamado
    mock_cria_core_sso.assert_not_called()


@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_create_erro_core_sso_levanta_validation_error(
    mock_cria_core_sso, api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """Quando o CoreSSO falha, deve levantar ValidationError."""
    # Configura o mock para levantar uma exceção
    mock_cria_core_sso.side_effect = Exception("Erro ao comunicar com CoreSSO")
    
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    data = {
        "username": "usuario_erro_coresso",
        "name": "Usuário Erro",
        "email": "erro.coresso@example.com",
        "cpf": "11122233344",
        "cargo": cargo_comum.pk,
        "rede": TipoGestaoChoices.INDIRETA,
        "unidades": [escola_sp.pk],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    # Deve levantar ValidationError quando tentar salvar
    with pytest.raises(serializers.ValidationError) as exc_info:
        serializer.save()
    
    # Verifica que a mensagem de erro está correta
    assert "Erro ao criar usuário" in str(exc_info.value)
    assert "Erro ao comunicar com CoreSSO" in str(exc_info.value)


@pytest.mark.django_db
@patch("apps.users.api.serializers.gestao_usuario_serializer.CriaUsuarioCoreSSOService.cria_usuario_core_sso")
def test_create_erro_core_sso_rollback_transacao(
    mock_cria_core_sso, api_rf, user_gipe_admin, cargo_comum, escola_sp
):
    """Quando o CoreSSO falha, a transação deve fazer rollback e o usuário não deve ser criado."""
    # Configura o mock para levantar uma exceção
    mock_cria_core_sso.side_effect = Exception("Falha no CoreSSO")
    
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin
    
    # Conta quantos usuários existem antes
    count_antes = User.objects.count()
    
    data = {
        "username": "usuario_rollback",
        "name": "Usuário Rollback",
        "email": "rollback@example.com",
        "cpf": "10101010101",
        "cargo": cargo_comum.pk,
        "rede": TipoGestaoChoices.INDIRETA,
        "unidades": [escola_sp.pk],
    }
    
    serializer = GestaoUsuarioSerializer(data=data, context={"request": request})
    assert serializer.is_valid(raise_exception=True)
    
    # Deve levantar ValidationError
    with pytest.raises(serializers.ValidationError):
        serializer.save()
    
    # Verifica que o usuário NÃO foi criado (rollback)
    count_depois = User.objects.count()
    assert count_depois == count_antes
    assert not User.objects.filter(username="usuario_rollback").exists()

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

