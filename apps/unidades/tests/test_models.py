import pytest
from django.core.exceptions import ValidationError
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices, TipoGestaoChoices


@pytest.fixture
def dre():
    return Unidade.objects.create(
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede=TipoGestaoChoices.DIRETA,
        codigo_eol='100001',
        nome='DRE Leste',
        sigla='DLE'
    )


@pytest.mark.django_db
def test_criar_unidade_tipo_adm(dre):
    adm = Unidade.objects.create(
        tipo_unidade=TipoUnidadeChoices.ADM,
        rede=TipoGestaoChoices.INDIRETA,
        codigo_eol='200002',
        nome='Gabinete Central',
        sigla='GAB',
        dre=dre,
    )
    assert adm.tipo_unidade == TipoUnidadeChoices.ADM
    assert adm.rede == TipoGestaoChoices.INDIRETA
    assert adm.dre == dre
    assert str(adm) == f"{adm.nome} ({adm.codigo_eol})"


@pytest.mark.django_db
def test_dre_nao_deve_ter_campo_dre_preenchido(dre):
    dre_invalida = Unidade(
        tipo_unidade=TipoUnidadeChoices.DRE,
        rede=TipoGestaoChoices.INDIRETA,
        codigo_eol='400004',
        nome='DRE Inválida',
        sigla='DRI',
        dre=dre
    )
    with pytest.raises(ValidationError):
        dre_invalida.full_clean()


@pytest.mark.django_db
def test_unidade_deve_apontar_para_dre_valida():
    dre_falsa = Unidade.objects.create(
        tipo_unidade=TipoUnidadeChoices.ADM,
        rede=TipoGestaoChoices.DIRETA,
        codigo_eol='600006',
        nome='Unidade ADM que não deveria ser DRE',
        sigla='UAD'
    )
    unidade = Unidade(
        tipo_unidade=TipoUnidadeChoices.ADM,
        rede=TipoGestaoChoices.INDIRETA,
        codigo_eol='500005',
        nome='Unidade com DRE inválida',
        sigla='INV',
        dre=dre_falsa
    )
    with pytest.raises(ValidationError):
        unidade.full_clean()


@pytest.mark.django_db
def test_manager_dres(dre):
    dres = Unidade.dres.all()
    assert dre in dres
    assert all(u.tipo_unidade == TipoUnidadeChoices.DRE for u in dres)