from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework.exceptions import ValidationError
from apps.unidades.models.unidades import Unidade, TipoUnidadeChoices, TipoGestaoChoices

User = get_user_model()

class GestaoUnidadeSerializer(serializers.ModelSerializer):
    """
    Serializer de criação/edição.
    - Recebe `dre` como UUID no payload (quando aplicável).
    - Controle de escopo PF/GIPE via validação.
    """
    dre = serializers.UUIDField(required=False,
        allow_null=True,
        error_messages={
            "invalid": "A DRE deve ser um UUID válido."
        }
    )
    tipo_unidade = serializers.ChoiceField(
        choices=TipoUnidadeChoices.choices,
        required=True,
        allow_null=False,
        error_messages={
            "required": "O tipo de unidade é obrigatório.",
            "null": "O tipo de unidade não pode ser nulo.",
            "invalid_choice": "Tipo de unidade inválido."
        }
    )
    nome = serializers.CharField(
        allow_blank=False,
        error_messages={
            "required": "O nome da unidade é obrigatório.",
            "blank": "O nome da unidade não pode ser vazio."
        }
    )
    rede = serializers.ChoiceField(
        choices=TipoGestaoChoices.choices,
        error_messages={
            "required": "A rede é obrigatória.",
            "blank": "A rede não pode ser vazia.",
            "invalid_choice": "Opção de rede inválida."
        }
    )
    codigo_eol = serializers.CharField(
        min_length=6,
        allow_blank=False,
        validators=[
            UniqueValidator(
                queryset=Unidade.objects.all(),
                message="Já existe uma unidade cadastrada com este código EOL."
            )
        ],
        error_messages={
            "required": "O código EOL é obrigatório.",
            "blank": "O código EOL não pode ser vazio.",
            "min_length": "O código EOL deve ter no mínimo 6 caracteres.",
            "invalid": "Código EOL inválido."
        }
    )

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
            _, first_error_list = next(iter(self.errors.items()))
            message = (
                first_error_list[0]
                if isinstance(first_error_list, list)
                else str(first_error_list)
            )

            if isinstance(self._errors, dict) and "detail" in self._errors:
                error_dict = self._errors
            else:
                error_dict = {"detail": message}

            self._errors = error_dict

            if raise_exception:
                raise serializers.ValidationError(self._errors)

        return valid

    def create(self, validated_data):
        try:
            dre_uuid = validated_data.pop("dre", None)

            dre_obj = None
            if dre_uuid:
                dre_obj = Unidade.objects.get(uuid=dre_uuid)

            unidade = Unidade.objects.create(dre=dre_obj, **validated_data)
            unidade.full_clean()
            unidade.save()
            return unidade
        except Exception as e:
            raise ValidationError({"detail": str(e)})

    def update(self, instance, validated_data):
        try:
            dre_uuid = validated_data.pop("dre", None)

            # atualiza campos simples
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            # Se está mudando para tipo DRE, limpa a referência de DRE
            if instance.tipo_unidade == TipoUnidadeChoices.DRE:
                instance.dre = None
            # Caso contrário, atualiza a DRE se vier no payload
            elif "dre" in self.initial_data:
                if dre_uuid:
                    instance.dre = Unidade.objects.get(uuid=dre_uuid)
                else:
                    instance.dre = None

            instance.full_clean()
            instance.save()
            return instance
        except Exception as e:
                raise ValidationError({"detail": str(e)})


class GestaoUnidadeListaSerializer(serializers.ModelSerializer):
    tipo_unidade_label = serializers.CharField(source="get_tipo_unidade_display", read_only=True)
    rede_label = serializers.CharField(source="get_rede_display", read_only=True)
    dre_nome = serializers.SerializerMethodField()
    dre_uuid = serializers.SerializerMethodField()
    sigla = serializers.SerializerMethodField()
    data_inativacao_formatada = serializers.SerializerMethodField()
    responsavel_inativacao_nome = serializers.SerializerMethodField()

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
            "data_inativacao",
            "data_inativacao_formatada",
            "responsavel_inativacao",
            "responsavel_inativacao_nome",
            "motivo_inativacao",
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
    
    def get_data_inativacao_formatada(self, obj):
        if not obj.data_inativacao:
            return None

        data_local = timezone.localtime(obj.data_inativacao)
        return data_local.strftime("%d/%m/%Y às %H:%Mh.")
    
    def get_responsavel_inativacao_nome(self, obj):
        if not obj.responsavel_inativacao:
            return None

        try:
            user = User.objects.only("name").get(
                username=obj.responsavel_inativacao
            )
            return user.name
        except User.DoesNotExist:
            return None