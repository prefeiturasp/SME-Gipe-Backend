from django.contrib import admin
from .models.unidades import Unidade


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'sigla',
        'codigo_eol',
        'tipo_unidade',
        'rede',
        'dre',
    )
    list_filter = (
        'tipo_unidade',
        'rede',
    )
    search_fields = (
        'nome',
        'codigo_eol',
        'sigla',
    )
    autocomplete_fields = ['dre']
    ordering = ['tipo_unidade', 'nome']