from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UnidadeMiniSerializer(serializers.Serializer):
    codigo_eol = serializers.CharField()
    nome = serializers.CharField()
    sigla = serializers.CharField()
    dre_codigo_eol = serializers.CharField(source="dre.codigo_eol", allow_null=True)

class UserMeSerializer(serializers.ModelSerializer):
    perfil_acesso = serializers.SerializerMethodField()
    unidades = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "username",
            "name",
            "email",
            "cpf",
            "rede",
            "is_core_sso",
            "is_validado",
            "perfil_acesso",
            "unidades",
        )

    def get_perfil_acesso(self, obj):
        cargo = getattr(obj, "cargo", None)
        if not cargo:
            return None
        return {
            "codigo": cargo.codigo,
            "nome": cargo.nome,
        }

    def get_unidades(self, obj):
        unidades = obj.unidades.select_related("dre").all()
        resultado = []

        for u in unidades:
            if u.tipo_unidade == "DRE":
                resultado.append({
                    "ue": {
                        "codigo_eol": None,
                        "nome": None,
                        "sigla": None,
                    },
                    "dre": {
                        "codigo_eol": u.codigo_eol,
                        "nome": u.nome,
                        "sigla": u.sigla,
                    }
                })
            else:
                resultado.append({
                    "ue": {
                        "codigo_eol": u.codigo_eol,
                        "nome": u.nome,
                        "sigla": u.sigla,
                    },
                    "dre": {
                        "codigo_eol": u.dre.codigo_eol if u.dre else None,
                        "nome": u.dre.nome if u.dre else None,
                        "sigla": u.dre.sigla if u.dre else None,
                    }
                })
                
        return resultado