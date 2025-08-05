from rest_framework import serializers
from apps.unidades.models.unidades import Unidade


class UnidadeSerializer(serializers.ModelSerializer):
    dre_nome = serializers.CharField(source='dre.nome', read_only=True)
    dre_codigo_eol = serializers.CharField(source='dre.codigo_eol', read_only=True)

    class Meta:
        model = Unidade
        fields = [
            'uuid',
            'codigo_eol',
            'tipo_unidade',
            'nome',
            'sigla',
            'rede',
            'dre_codigo_eol',
            'dre_nome',
        ]