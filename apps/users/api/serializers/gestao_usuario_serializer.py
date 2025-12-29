from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.unidades.models.unidades import TipoGestaoChoices, Unidade, TipoUnidadeChoices
from django.db import transaction
from apps.users.services.usuario_core_sso_service import CriaUsuarioCoreSSOService

User = get_user_model()

def format_cpf(cpf: str) -> str:
    """
    Formata CPF no padrão 000.000.000-00.
    Se não tiver 11 dígitos, retorna como veio.
    """
    if not cpf:
        return ""
    digits = "".join(filter(str.isdigit, cpf))
    if len(digits) != 11:
        return cpf
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class GestaoUsuarioListaSerializer(serializers.ModelSerializer):
    """
    Serializer para exibição na tabela de usuários (listagem).
    Campos 'humanizados' para a tela.
    """

    perfil = serializers.CharField(source="cargo.nome", read_only=True)
    nome = serializers.CharField(source="name", read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    data_solicitacao = serializers.DateTimeField(
        source="date_joined",
        format="%d/%m/%Y",
        read_only=True,
    )
    rf_ou_cpf = serializers.SerializerMethodField()
    rede = serializers.SerializerMethodField()
    diretoria_regional = serializers.SerializerMethodField()
    unidade_educacional = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "uuid",              
            "perfil",             
            "username",             
            "nome",               
            "data_solicitacao",   
            "rf_ou_cpf",          
            "email",
            "rede",               
            "diretoria_regional",
            "unidade_educacional",
            "is_validado",
            "is_active",
        ]


    def get_rf_ou_cpf(self, obj) -> str:
        """
        Regra:
        - Se tiver CPF cadastrado -> devolve CPF formatado.
        - Senão, usa o username (RF ou CPF bruto).
        """
        if obj.cpf:
            return format_cpf(obj.cpf)
        return obj.username or ""


    def get_rede(self, obj) -> str:
        """
        Usa o display do choices ou '-' se vazio.
        """
        try:
            label = obj.get_rede_display()
        except Exception:
            label = obj.rede or ""
        return label or "-"

    def get_diretoria_regional(self, obj):
        """
        Regra:
        - Se o usuário tiver unidade do tipo DRE -> usa essa unidade como DRE.
        - Senão, se tiver unidade escolar com dre associado -> usa unidade.dre.nome.
        - Senão, retorna '-'.
        """

        dre_unidade = obj.unidades.filter(
            tipo_unidade=TipoUnidadeChoices.DRE
        ).first()
        if dre_unidade:
            return dre_unidade.nome


        unidade_escolar = obj.unidades.exclude(
            tipo_unidade=TipoUnidadeChoices.DRE
        ).select_related("dre").first()

        if unidade_escolar and unidade_escolar.dre:
            return unidade_escolar.dre.nome

        return "-"


    def get_unidade_educacional(self, obj):
        """
        Regra:
        - Para Diretor/Assistente/etc: pega primeira unidade que não seja DRE.
        - Para Ponto Focal / GIPE (que normalmente só tem DRE ou nenhuma) -> '-'.
        """
        unidade_escolar = obj.unidades.exclude(
            tipo_unidade=TipoUnidadeChoices.DRE
        ).first()

        if unidade_escolar:
            return unidade_escolar.nome

        return "-"


class GestaoUsuarioSerializer(serializers.ModelSerializer):
    unidades = serializers.PrimaryKeyRelatedField(
        queryset=Unidade.objects.all(),
        many=True
    )
    is_app_admin = serializers.BooleanField(required=False)
    

    class Meta:
        model = User
        fields = [
            "uuid",
            "username", 
            "name", 
            "email", 
            "cpf",
            "cargo", 
            "rede",
            "unidades",
            "is_validado",
            "is_app_admin",
            "is_core_sso",
        ]

    def validate_unidades(self, unidades):
        """
        Ponto Focal só pode atribuir unidades da própria DRE.
        GIPE pode qualquer unidade.
        Diretor não deveria estar criando usuários, mas se estiver, bloqueia.
        """
        request = self.context["request"]
        user = request.user
        
        if not user.is_app_admin:
            raise serializers.ValidationError(
                "Você não tem permissão para definir unidades de outros usuários."
        )

        if not user.is_gipe and not user.is_ponto_focal:
            raise serializers.ValidationError(
                "Você não tem permissão para definir unidades de outros usuários."
            )

        if user.is_ponto_focal:
            allowed_dres = set(
                user.unidades.values_list("codigo_eol", flat=True).distinct()
            )
            for u in unidades:
                if u.dre_id not in allowed_dres:
                    raise serializers.ValidationError(
                       "Ponto Focal só pode cadastrar usuários para unidades de sua DRE."
                    )

        return unidades

    def validate_is_app_admin(self, value):
        """
        Somente GIPE pode marcar outro usuário como admin.
        """
        request = self.context["request"]
        user = request.user
        if value and not user.is_gipe:
            raise serializers.ValidationError(
                "Somente usuários com perfil GIPE podem atribuir perfil administrador."
            )
        return value
    
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
        unidades = validated_data.pop("unidades", [])
        is_app_admin = validated_data.pop("is_app_admin", False)
        request = self.context["request"]
        user_request = request.user

        validated_data.setdefault("is_validado", True)


        if not user_request.is_gipe:
            is_app_admin = False
            
        try:
            
            with transaction.atomic():
                novo_user = User.objects.create_user(**validated_data)
                novo_user.unidades.set(unidades)
                novo_user.is_app_admin = is_app_admin
                novo_user.save(update_fields=["is_app_admin"])
                
                rede = validated_data.get("rede", None)
                
                if rede and rede == TipoGestaoChoices.INDIRETA:
                
                    dados_usuario_a_ser_enviado_coresso = {
                        "login": novo_user.username,
                        "nome": novo_user.name,
                        "email": novo_user.email,
                    }
                    
                    CriaUsuarioCoreSSOService.cria_usuario_core_sso(dados_usuario_a_ser_enviado_coresso)
                
        except Exception as e:
            raise serializers.ValidationError(f"Erro ao criar usuário: {str(e)}")

        return novo_user

    def update(self, instance, validated_data):
        unidades = validated_data.pop("unidades", None)
        is_app_admin = validated_data.pop("is_app_admin", None)
        request = self.context["request"]
        user_request = request.user

        # Campos sensíveis: só GIPE pode mexer em is_app_admin
        if is_app_admin is not None:
            if user_request.is_gipe:
                instance.is_app_admin = is_app_admin
            # se não for GIPE, simplesmente ignora

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if unidades is not None:
            self.validate_unidades(unidades)  
            instance.unidades.set(unidades)

        return instance
    

class GestaoUsuarioRetrieveSerializer(GestaoUsuarioSerializer):
    """
    Serializer para exibir detalhes completos do usuário.
    """
    is_active = serializers.BooleanField(read_only=True)
    codigo_eol_unidade = serializers.SerializerMethodField()
    codigo_eol_dre_da_unidade = serializers.SerializerMethodField()

    class Meta(GestaoUsuarioSerializer.Meta):
        fields = GestaoUsuarioSerializer.Meta.fields + [
            "is_active",
            "codigo_eol_unidade",
            "codigo_eol_dre_da_unidade",
        ]

    def get_codigo_eol_unidade(self, obj):
        primeira_unidade = obj.unidades.first()

        if not primeira_unidade:
            return None

        if primeira_unidade.tipo_unidade == TipoUnidadeChoices.DRE:
            return None

        return primeira_unidade.codigo_eol

    def get_codigo_eol_dre_da_unidade(self, obj):
        primeira_unidade = obj.unidades.first()

        if not primeira_unidade:
            return None

        if primeira_unidade.tipo_unidade == TipoUnidadeChoices.DRE:
            return primeira_unidade.codigo_eol

        if primeira_unidade.dre:
            return primeira_unidade.dre.codigo_eol

        return None