from rest_framework import serializers
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices


class UnidadeSerializer(serializers.ModelSerializer):
    dre_nome = serializers.CharField(source='dre.nome', read_only=True)
    dre_codigo_eol = serializers.CharField(source='dre.codigo_eol', read_only=True)
    tipo_nome_ue = serializers.SerializerMethodField()

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
            'tipo_nome_ue',
        ]

    def get_tipo_nome_ue(self, obj):
        if obj.tipo_unidade != TipoUnidadeChoices.DRE:
            return f"{obj.tipo_unidade} {obj.nome}"
        return None