import pytest
from django.utils import timezone
from unittest.mock import Mock, patch
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.unidades.api.serializers.gestao_unidade_serializer import (
    GestaoUnidadeSerializer,
    GestaoUnidadeListaSerializer,
)
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices, TipoGestaoChoices
from apps.helpers.exceptions import InternalError, SmeIntegracaoException

User = get_user_model()

@pytest.mark.django_db
class TestGestaoUnidadeSerializer:
    """Testes para GestaoUnidadeSerializer (create/update)."""

    def test_validate_dre_none_permitido(self, api_rf, user_gipe_admin):
        """DRE None é permitido (quando a própria unidade é DRE)."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        serializer = GestaoUnidadeSerializer(context={"request": request})
        result = serializer.validate_dre(None)

        assert result is None

    def test_validate_dre_nao_existe(self, api_rf, user_gipe_admin):
        """Erro se DRE UUID não existe."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        serializer = GestaoUnidadeSerializer(context={"request": request})

        import uuid
        fake_uuid = uuid.uuid4()

        with pytest.raises(ValidationError) as excinfo:
            serializer.validate_dre(fake_uuid)

        assert "DRE informada não existe" in str(excinfo.value)

    def test_validate_dre_tipo_incorreto(self, api_rf, user_gipe_admin, escola_sp):
        """Erro se a unidade selecionada não é tipo DRE."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        serializer = GestaoUnidadeSerializer(context={"request": request})

        with pytest.raises(ValidationError) as excinfo:
            serializer.validate_dre(escola_sp.uuid)

        assert "deve ser do tipo DRE" in str(excinfo.value)

    def test_validate_dre_gipe_aceita_qualquer_dre(
        self, api_rf, user_gipe_admin, dre_sp, dre_outra
    ):
        """GIPE admin pode cadastrar unidades em qualquer DRE."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        serializer = GestaoUnidadeSerializer(context={"request": request})

        # Deve aceitar ambas DREs
        assert serializer.validate_dre(dre_sp.uuid) == dre_sp.uuid
        assert serializer.validate_dre(dre_outra.uuid) == dre_outra.uuid

    def test_validate_dre_pf_apenas_sua_dre(
        self, api_rf, user_pf_admin, dre_sp, dre_outra
    ):
        """Ponto Focal só pode cadastrar unidades na sua DRE."""
        request = api_rf.post("/fake-url/")
        request.user = user_pf_admin

        serializer = GestaoUnidadeSerializer(context={"request": request})

        # Deve aceitar dre_sp (sua DRE)
        assert serializer.validate_dre(dre_sp.uuid) == dre_sp.uuid

        # Deve rejeitar dre_outra
        with pytest.raises(ValidationError) as excinfo:
            serializer.validate_dre(dre_outra.uuid)

        assert "Ponto Focal só pode cadastrar unidades na sua DRE" in str(excinfo.value)


    def test_validate_dre_nao_pode_ter_dre_pai(self, api_rf, user_gipe_admin, dre_sp):
        """Unidades do tipo DRE não devem referenciar outra DRE."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        data = {
            "tipo_unidade": TipoUnidadeChoices.DRE,
            "dre": dre_sp.uuid,
            "nome": "Nova DRE",
            "rede": "DIRETA",
            "codigo_eol": "111111",
        }

        serializer = GestaoUnidadeSerializer(data=data, context={"request": request})

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        assert "não devem referenciar outra DRE" in str(excinfo.value)

    def test_validate_nao_dre_precisa_dre(self, api_rf, user_gipe_admin):
        """Unidades que não são DRE precisam ter DRE definida."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEI,
            "nome": "EMEI Sem DRE",
            "rede": "DIRETA",
            "codigo_eol": "222222",
        }

        serializer = GestaoUnidadeSerializer(data=data, context={"request": request})

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        assert "DRE é obrigatória" in str(excinfo.value)

    def test_validate_update_dre_nao_pode_ter_dre(
        self, api_rf, user_gipe_admin, dre_sp, dre_outra
    ):
        """Na edição, se mudar para tipo DRE, não pode ter dre."""
        request = api_rf.patch("/fake-url/")
        request.user = user_gipe_admin

        # Simula uma escola existente
        escola = Unidade.objects.create(
            codigo_eol="333333",
            nome="EMEI Original",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
            dre=dre_sp,
        )

        data = {
            "tipo_unidade": TipoUnidadeChoices.DRE,
            "dre": dre_outra.uuid,
        }

        serializer = GestaoUnidadeSerializer(
            instance=escola, data=data, partial=True, context={"request": request}
        )

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        assert "não devem referenciar outra DRE" in str(excinfo.value)


    def test_is_valid_retorna_erro_customizado(self, api_rf, user_gipe_admin):
        """is_valid deve retornar erro no formato {detail: mensagem}."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        data = {
            "tipo_unidade": TipoUnidadeChoices.EMEI,
            # falta nome, codigo_eol, etc
        }

        serializer = GestaoUnidadeSerializer(data=data, context={"request": request})

        assert not serializer.is_valid()
        assert "detail" in serializer.errors

    def test_is_valid_preserva_quando_erro_ja_possui_detail(
        self, monkeypatch, api_rf, user_gipe_admin
    ):
        """Não deve sobrescrever mensagens que já chegam em `detail`."""
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        serializer = GestaoUnidadeSerializer(data={}, context={"request": request})

        def fake_super_is_valid(self, raise_exception=False):
            self._errors = {"detail": "Erro externo"}
            return False

        monkeypatch.setattr(serializers.ModelSerializer, "is_valid", fake_super_is_valid)

        assert not serializer.is_valid()
        assert serializer.errors == {"detail": "Erro externo"}

    def test_update_nao_dre_remove_dre_com_none_explicito(
        self, api_rf, user_gipe_admin, dre_sp
    ):
        """update de unidade não-DRE com dre=None explícito no payload deve limpar a DRE."""
        request = api_rf.patch("/fake-url/")
        request.user = user_gipe_admin

        # Cria uma escola vinculada à dre_sp
        escola = Unidade.objects.create(
            codigo_eol="131313",
            nome="EMEF Teste",
            tipo_unidade=TipoUnidadeChoices.EMEF,
            rede="DIRETA",
            dre=dre_sp,
        )

        # Tenta remover a DRE com None explícito
        # Nota: isso deve falhar na validação porque unidades não-DRE precisam ter DRE
        data = {
            "dre": None,
        }

        serializer = GestaoUnidadeSerializer(
            instance=escola, data=data, partial=True, context={"request": request}
        )
        
        # Deve falhar porque EMEF não pode ficar sem DRE
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        assert "DRE é obrigatória" in str(excinfo.value)

    def test_update_nao_dre_com_dre_none_no_payload_bypass_validacao(
        self, api_rf, user_gipe_admin, dre_sp
    ):
        """Testa o else do elif que define instance.dre = None quando dre_uuid é None."""
        request = api_rf.patch("/fake-url/")
        request.user = user_gipe_admin

        # Cria uma escola vinculada à dre_sp
        escola = Unidade.objects.create(
            codigo_eol="141414",
            nome="EMEF Teste Bypass",
            tipo_unidade=TipoUnidadeChoices.EMEF,
            rede="DIRETA",
            dre=dre_sp,
        )

        data = {
            "nome": "Nome atualizado",
            "dre": None,
        }

        serializer = GestaoUnidadeSerializer(
            instance=escola, data=data, partial=True, context={"request": request}
        )

        # Mocka o método validate para bypassar a validação que impede dre=None
        def mock_validate(self, attrs):
            return attrs

        with patch.object(GestaoUnidadeSerializer, 'validate', mock_validate):
            assert serializer.is_valid()
            
            # Mocka full_clean para não falhar na validação do modelo
            with patch.object(escola, 'full_clean'):
                unidade = serializer.save()
                
                # Verifica que instance.dre foi definido como None
                assert unidade.dre is None
                assert unidade.nome == "Nome atualizado"


@pytest.mark.django_db
class TestGestaoUnidadeListaSerializer:
    """Testes para GestaoUnidadeListaSerializer (listagem/leitura)."""

    def test_serializa_dre(self, dre_sp):
        """Serialização de uma DRE."""
        serializer = GestaoUnidadeListaSerializer(dre_sp)
        data = serializer.data

        assert data["uuid"] == str(dre_sp.uuid)
        assert data["codigo_eol"] == dre_sp.codigo_eol
        assert data["nome"] == dre_sp.nome
        assert data["tipo_unidade"] == TipoUnidadeChoices.DRE
        assert data["tipo_unidade_label"] == "DRE"
        assert data["rede"] == "DIRETA"
        assert data["rede_label"] == "Direta"
        assert data["dre_nome"] == dre_sp.nome  # DRE retorna seu próprio nome
        assert data["dre_uuid"] == str(dre_sp.uuid)  # DRE retorna seu próprio UUID
        assert data["sigla"] == dre_sp.sigla
        assert data["ativa"] == dre_sp.ativa

    def test_serializa_escola_com_dre(self, escola_sp, dre_sp):
        """Serialização de uma escola vinculada a uma DRE."""
        serializer = GestaoUnidadeListaSerializer(escola_sp)
        data = serializer.data

        assert data["uuid"] == str(escola_sp.uuid)
        assert data["codigo_eol"] == escola_sp.codigo_eol
        assert data["nome"] == escola_sp.nome
        assert data["tipo_unidade"] == TipoUnidadeChoices.EMEI
        assert data["tipo_unidade_label"] == "EMEI"
        assert data["dre_nome"] == dre_sp.nome
        assert data["dre_uuid"] == str(dre_sp.uuid)

    def test_serializa_escola_sem_dre(self, db):
        """Serialização de uma escola sem DRE retorna '-' para dre_nome."""
        escola_sem_dre = Unidade.objects.create(
            codigo_eol="888888",
            nome="EMEI Sem DRE",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
        )

        serializer = GestaoUnidadeListaSerializer(escola_sem_dre)
        data = serializer.data

        assert data["dre_nome"] == "-"
        assert data["dre_uuid"] is None

    def test_get_dre_nome_dre_retorna_proprio_nome(self, dre_sp):
        """get_dre_nome para DRE retorna o próprio nome."""
        serializer = GestaoUnidadeListaSerializer()
        result = serializer.get_dre_nome(dre_sp)

        assert result == dre_sp.nome

    def test_get_dre_nome_escola_retorna_nome_dre(self, escola_sp, dre_sp):
        """get_dre_nome para escola retorna o nome da DRE vinculada."""
        serializer = GestaoUnidadeListaSerializer()
        result = serializer.get_dre_nome(escola_sp)

        assert result == dre_sp.nome

    def test_get_dre_nome_sem_dre_retorna_traco(self, db):
        """get_dre_nome para unidade sem DRE retorna '-'."""
        escola_sem_dre = Unidade.objects.create(
            codigo_eol="999999",
            nome="EMEI Sem DRE",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
        )

        serializer = GestaoUnidadeListaSerializer()
        result = serializer.get_dre_nome(escola_sem_dre)

        assert result == "-"

    def test_get_dre_uuid_dre_retorna_proprio_uuid(self, dre_sp):
        """get_dre_uuid para DRE retorna o próprio UUID."""
        serializer = GestaoUnidadeListaSerializer()
        result = serializer.get_dre_uuid(dre_sp)

        assert result == str(dre_sp.uuid)

    def test_get_dre_uuid_escola_retorna_uuid_dre(self, escola_sp, dre_sp):
        """get_dre_uuid para escola retorna o UUID da DRE vinculada."""
        serializer = GestaoUnidadeListaSerializer()
        result = serializer.get_dre_uuid(escola_sp)

        assert result == str(dre_sp.uuid)

    def test_get_dre_uuid_sem_dre_retorna_none(self, db):
        """get_dre_uuid para unidade sem DRE retorna None."""
        escola_sem_dre = Unidade.objects.create(
            codigo_eol="101010",
            nome="EMEI Sem DRE",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
        )

        serializer = GestaoUnidadeListaSerializer()
        result = serializer.get_dre_uuid(escola_sem_dre)

        assert result is None

    def test_lista_multiplas_unidades(self, dre_sp, dre_outra, escola_sp, escola_outra):
        """Serialização de múltiplas unidades."""
        unidades = [dre_sp, dre_outra, escola_sp, escola_outra]
        serializer = GestaoUnidadeListaSerializer(unidades, many=True)
        data = serializer.data

        assert len(data) == 4
        assert data[0]["nome"] == dre_sp.nome
        assert data[1]["nome"] == dre_outra.nome
        assert data[2]["nome"] == escola_sp.nome
        assert data[3]["nome"] == escola_outra.nome


@pytest.mark.django_db
class TestGestaoUnidadeSerializerExceptions:

    def test_create_erro_inesperado_dispara_validation_error(self, api_rf, user_gipe_admin):
        request = api_rf.post("/fake-url/")
        request.user = user_gipe_admin

        dre_obj = Unidade.objects.create(
            tipo_unidade=TipoUnidadeChoices.DRE,
            nome="DRE Teste",
            rede=TipoGestaoChoices.INDIRETA,
            codigo_eol="999999",
            ativa=True
        )

        data = {
            "tipo_unidade": TipoUnidadeChoices.CEI,
            "nome": "Escola Teste",
            "rede": TipoGestaoChoices.INDIRETA,
            "codigo_eol": "123456",
            "dre": str(dre_obj.uuid),
        }

        serializer = GestaoUnidadeSerializer(data=data, context={"request": request})

        assert serializer.is_valid(raise_exception=True)

        with patch.object(Unidade.objects, "create", side_effect=Exception("Erro inesperado")):
            with pytest.raises(ValidationError) as excinfo:
                serializer.save()

        assert "Erro inesperado" in str(excinfo.value)
        assert excinfo.value.detail == {"detail": "Erro inesperado"}
    
    def test_data_inativacao_formatada_quando_existe(self, dre_sp):
        data = timezone.now()

        unidade = Unidade.objects.create(
            codigo_eol="999001",
            nome="Unidade Inativa",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
            dre=dre_sp,
            ativa=False,
            data_inativacao=data,
        )

        serializer = GestaoUnidadeListaSerializer(unidade)
        result = serializer.data["data_inativacao_formatada"]

        data_local = timezone.localtime(data).strftime("%d/%m/%Y às %H:%Mh.")
        assert result == data_local

    def test_data_inativacao_formatada_quando_none(self, dre_sp):
        unidade = Unidade.objects.create(
            codigo_eol="999002",
            nome="Unidade Ativa",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
            dre=dre_sp,
            ativa=True,
            data_inativacao=None,
        )

        serializer = GestaoUnidadeListaSerializer(unidade)
        assert serializer.data["data_inativacao_formatada"] is None
    
    def test_responsavel_inativacao_nome_quando_existe(self, dre_sp):
        user = User.objects.create_user(
            username="joao.teste",
            name="João da Silva",
        )

        unidade = Unidade.objects.create(
            codigo_eol="999003",
            nome="Unidade Inativa",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
            dre=dre_sp,
            ativa=False,
            responsavel_inativacao=user.username,
        )

        serializer = GestaoUnidadeListaSerializer(unidade)
        assert serializer.data["responsavel_inativacao_nome"] == "João da Silva"

    def test_responsavel_inativacao_nome_quando_username_nao_existe(self, dre_sp):
        unidade = Unidade.objects.create(
            codigo_eol="999004",
            nome="Unidade Inativa",
            tipo_unidade=TipoUnidadeChoices.EMEI,
            rede="DIRETA",
            dre=dre_sp,
            ativa=False,
            responsavel_inativacao="123456",
        )

        serializer = GestaoUnidadeListaSerializer(unidade)
        assert serializer.data["responsavel_inativacao_nome"] is None

@pytest.mark.django_db
def test_validate_consulta_eol_sucesso(
    api_rf, user_gipe_admin, dre_sp
):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    data = {
        "tipo_unidade": TipoUnidadeChoices.EMEI,
        "nome": "Escola OK",
        "rede": TipoGestaoChoices.DIRETA,
        "codigo_eol": "555555",
        "dre": str(dre_sp.uuid),
    }

    serializer = GestaoUnidadeSerializer(
        data=data,
        context={"request": request}
    )

    with patch(
        "apps.unidades.api.serializers.gestao_unidade_serializer.ConsultaDadosEolService.consultar_dados_unidade"
    ) as mock_consulta:

        mock_consulta.return_value = {"nome": "Teste"}

        assert serializer.is_valid(raise_exception=True)

@pytest.mark.django_db
def test_validate_consulta_eol_sme_exception(
    api_rf, user_gipe_admin, dre_sp
):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    data = {
        "tipo_unidade": TipoUnidadeChoices.EMEI,
        "nome": "Escola Erro",
        "rede": TipoGestaoChoices.DIRETA,
        "codigo_eol": "666666",
        "dre": str(dre_sp.uuid),
    }

    serializer = GestaoUnidadeSerializer(
        data=data,
        context={"request": request}
    )

    with patch(
        "apps.unidades.api.serializers.gestao_unidade_serializer.ConsultaDadosEolService.consultar_dados_unidade",
        side_effect=SmeIntegracaoException()
    ):

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        assert "verifique se o código" in str(excinfo.value)

@pytest.mark.django_db
def test_validate_consulta_eol_internal_error(
    api_rf, user_gipe_admin, dre_sp
):
    request = api_rf.post("/fake/")
    request.user = user_gipe_admin

    data = {
        "tipo_unidade": TipoUnidadeChoices.EMEI,
        "nome": "Escola Erro Interno",
        "rede": TipoGestaoChoices.DIRETA,
        "codigo_eol": "777777",
        "dre": str(dre_sp.uuid),
    }

    serializer = GestaoUnidadeSerializer(
        data=data,
        context={"request": request}
    )

    with patch(
        "apps.unidades.api.serializers.gestao_unidade_serializer.ConsultaDadosEolService.consultar_dados_unidade",
        side_effect=InternalError()
    ):

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        assert "Não foi possível validar" in str(excinfo.value)

@pytest.mark.django_db

def test_update_troca_dre(
    api_rf, user_gipe_admin, dre_sp, dre_outra
):

    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin

    escola = Unidade.objects.create(
        codigo_eol="777777",
        nome="Teste",
        tipo_unidade=TipoUnidadeChoices.EMEI,
        rede="DIRETA",
        dre=dre_sp,
    )

    data = {
        "dre": str(dre_outra.uuid),
    }

    serializer = GestaoUnidadeSerializer(
        instance=escola,
        data=data,
        partial=True,
        context={"request": request},
    )

    with patch(
        "apps.unidades.api.serializers.gestao_unidade_serializer.ConsultaDadosEolService.consultar_dados_unidade"
    ) as mock_consulta:

        mock_consulta.return_value = True

        assert serializer.is_valid()

        with patch.object(escola, "full_clean"):
            unidade = serializer.save()

    assert unidade.dre == dre_outra

@pytest.mark.django_db
def test_update_exception_dispara_validation_error(
    api_rf, user_gipe_admin, dre_sp
):

    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin

    escola = Unidade.objects.create(
        codigo_eol="555555",
        nome="Original",
        tipo_unidade=TipoUnidadeChoices.EMEI,
        rede="DIRETA",
        dre=dre_sp,
    )

    data = {
        "nome": "Novo nome",
        "dre": str(dre_sp.uuid),
    }

    serializer = GestaoUnidadeSerializer(
        instance=escola,
        data=data,
        partial=True,
        context={"request": request},
    )

    with patch(
        "apps.unidades.api.serializers.gestao_unidade_serializer.ConsultaDadosEolService.consultar_dados_unidade"
    ):

        assert serializer.is_valid()

        with patch.object(escola, "full_clean", side_effect=Exception("Erro")):

            with pytest.raises(ValidationError) as excinfo:
                serializer.save()

    assert "Erro" in str(excinfo.value)

@pytest.mark.django_db
def test_update_dre_limpa_referencia_quando_instancia_e_dre(
    api_rf,
    user_gipe_admin,
    dre_sp,
):

    request = api_rf.patch("/fake/")
    request.user = user_gipe_admin

    dre_sp.dre = dre_sp
    dre_sp.save(update_fields=["dre"])

    data = {
        "nome": "Nome atualizado",
    }

    serializer = GestaoUnidadeSerializer(
        instance=dre_sp,
        data=data,
        partial=True,
        context={"request": request},
    )

    with patch(
        "apps.unidades.api.serializers.gestao_unidade_serializer.ConsultaDadosEolService.consultar_dados_unidade"
    ):

        assert serializer.is_valid()

        with patch.object(dre_sp, "full_clean"):
            unidade = serializer.save()

    assert unidade.dre is None