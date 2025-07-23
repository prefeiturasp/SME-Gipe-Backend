import pytest
from django.db import connection
from django.apps import apps
from apps import models_abstracts


class ModeloConcreto(models_abstracts.ModeloBase, models_abstracts.TemNome):
    class Meta:
        app_label = "unidades"
        db_table = "unidades_modeloconcreto"


@pytest.fixture(scope="function")
def modelo_concreto(db):
    # Cria tabela para o modelo concreto, que foi definido uma vez só no arquivo
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ModeloConcreto)

    yield ModeloConcreto

    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(ModeloConcreto)


@pytest.mark.django_db
def test_modelo_concreto_criacao(modelo_concreto):
    instance = modelo_concreto.objects.create(nome="Exemplo")
    assert instance.nome == "Exemplo"
    assert instance.uuid is not None
    assert instance.criado_em is not None
    assert instance.alterado_em is not None


@pytest.mark.django_db
def test_modelo_concreto_by_uuid(modelo_concreto):
    instance = modelo_concreto.objects.create(nome="Teste UUID")
    encontrado = modelo_concreto.by_uuid(instance.uuid)
    assert encontrado == instance


@pytest.mark.django_db
def test_modelo_concreto_by_id(modelo_concreto):
    instance = modelo_concreto.objects.create(nome="Teste ID")
    encontrado = modelo_concreto.by_id(instance.id)
    assert encontrado == instance


@pytest.mark.django_db
def test_modelo_concreto_get_valores(modelo_concreto):
    modelo_concreto.objects.create(nome="Valor 1")
    modelo_concreto.objects.create(nome="Valor 2")
    valores = modelo_concreto.get_valores()
    assert valores.count() == 2