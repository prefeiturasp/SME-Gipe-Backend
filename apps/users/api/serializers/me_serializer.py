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
            "is_app_admin",
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
        return [self._format_unidade(unidade) for unidade in unidades]

    def _format_unidade(self, unidade):
        return {
            "ue": self._format_ue(unidade),
            "dre": self._format_dre(unidade),
        }

    def _format_ue(self, unidade):
        if unidade.tipo_unidade == "DRE":
            return {
                "ue_uuid": None,
                "codigo_eol": None,
                "nome": None,
                "sigla": None,
            }

        return {
            "ue_uuid": unidade.uuid,
            "codigo_eol": unidade.codigo_eol,
            "nome": unidade.nome,
            "sigla": unidade.sigla,
        }

    def _format_dre(self, unidade):
        dre = unidade if unidade.tipo_unidade == "DRE" else unidade.dre
        return {
            "dre_uuid": getattr(dre, "uuid", None),
            "codigo_eol": getattr(dre, "codigo_eol", None),
            "nome": getattr(dre, "nome", None),
            "sigla": getattr(dre, "sigla", None),
        }
