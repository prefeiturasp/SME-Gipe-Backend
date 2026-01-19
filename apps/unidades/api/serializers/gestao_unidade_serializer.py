from rest_framework import serializers
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices


class GestaoUnidadeSerializer(serializers.ModelSerializer):
    """
    Serializer de criação/edição.
    - Recebe `dre` como UUID no payload (quando aplicável).
    - Controle de escopo PF/GIPE via validação.
    """
    dre = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Unidade
        fields = [
            "uuid",
            "tipo_unidade",
            "nome",
            "rede",
            "codigo_eol",
            "dre",     
            "sigla",
            "ativa",  
        ]
        read_only_fields = ["uuid"]

    def validate_dre(self, value):
        """
        - dre pode ser None quando a própria unidade é DRE.
        - quando vier, precisa existir e ser tipo DRE.
        - PF admin só pode atribuir DRE(s) dele.
        """
        request = self.context["request"]
        user = request.user

        if not value:
            return value

        try:
            dre_obj = Unidade.objects.get(uuid=value)
        except Unidade.DoesNotExist:
            raise serializers.ValidationError("DRE informada não existe.")

        if dre_obj.tipo_unidade != TipoUnidadeChoices.DRE:
            raise serializers.ValidationError("A unidade selecionada como DRE deve ser do tipo DRE.")

        if user.is_ponto_focal:
            allowed_dres = set(
                user.unidades
                    .filter(tipo_unidade=TipoUnidadeChoices.DRE)
                    .values_list("uuid", flat=True)
            )
            if dre_obj.uuid not in allowed_dres:
                raise serializers.ValidationError("Ponto Focal só pode cadastrar unidades na sua DRE.")

        return value

    def validate(self, attrs):
        """
        Regras adicionais:
        - Se tipo_unidade=DRE, não pode ter dre preenchida.
        - Se tipo_unidade!=DRE, dre deve existir.
        """
        tipo = attrs.get("tipo_unidade", getattr(self.instance, "tipo_unidade", None))
        dre_uuid = attrs.get("dre", None)

        if tipo == TipoUnidadeChoices.DRE and dre_uuid:
            raise serializers.ValidationError({"dre": "Unidades do tipo DRE não devem referenciar outra DRE."})

        if tipo != TipoUnidadeChoices.DRE and not dre_uuid:
            raise serializers.ValidationError({"dre": "Para unidades que não são DRE, a DRE é obrigatória."})

        return attrs
    
    def is_valid(self, raise_exception=False):

        valid = super().is_valid(raise_exception=False)
        if not valid:
            first_field, first_error_list = next(iter(self.errors.items()))
            message = (
                first_error_list[0]
                if isinstance(first_error_list, list)
                else str(first_error_list)
            )

            if isinstance(self._errors, dict) and "detail" in self._errors:
                error_dict = self._errors
            else:
                error_dict = {"detail": f"{first_field}: {message}"}

            self._errors = error_dict

            if raise_exception:
                raise serializers.ValidationError(self._errors)

        return valid

    def create(self, validated_data):
        dre_uuid = validated_data.pop("dre", None)

        dre_obj = None
        if dre_uuid:
            dre_obj = Unidade.objects.get(uuid=dre_uuid)

        unidade = Unidade.objects.create(dre=dre_obj, **validated_data)
        unidade.full_clean()
        unidade.save()
        return unidade

    def update(self, instance, validated_data):
        dre_uuid = validated_data.pop("dre", None)

        # atualiza campos simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # dre (se vier)
        if "dre" in self.initial_data:
            if dre_uuid:
                instance.dre = Unidade.objects.get(uuid=dre_uuid)
            else:
                instance.dre = None

        instance.full_clean()
        instance.save()
        return instance


class GestaoUnidadeListaSerializer(serializers.ModelSerializer):
    tipo_unidade_label = serializers.CharField(source="get_tipo_unidade_display", read_only=True)
    rede_label = serializers.CharField(source="get_rede_display", read_only=True)
    dre_nome = serializers.SerializerMethodField()
    dre_uuid = serializers.SerializerMethodField()
    sigla = serializers.SerializerMethodField()

    class Meta:
        model = Unidade
        fields = [
            "uuid",
            "codigo_eol",
            "nome",
            "tipo_unidade",
            "tipo_unidade_label",
            "rede",
            "rede_label",
            "dre_uuid",
            "dre_nome",
            "sigla",
            "ativa",
        ]

    def get_dre_nome(self, obj):
        if obj.tipo_unidade == TipoUnidadeChoices.DRE:
            return obj.nome
        return obj.dre.nome if obj.dre else "-"

    def get_dre_uuid(self, obj):
        if obj.tipo_unidade == TipoUnidadeChoices.DRE:
            return str(obj.uuid)
        return str(obj.dre.uuid) if obj.dre else None
    
    def get_sigla(self, obj):
        if obj.tipo_unidade == TipoUnidadeChoices.DRE:
            return obj.sigla
        return obj.dre.sigla if obj.dre else ""