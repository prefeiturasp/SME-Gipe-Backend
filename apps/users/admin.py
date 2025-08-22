from django import forms
from django.shortcuts import render
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm

from .models import User, Cargo
from apps.unidades.models.unidades import TipoGestaoChoices

User = get_user_model()


class CustomAdminPasswordChangeForm(AdminPasswordChangeForm):
    """
    Formulário personalizado para alteração de senha sem opção de desabilitar
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove o campo 'usable_password' se existir
        if 'usable_password' in self.fields:
            del self.fields['usable_password']


class CustomUserCreationForm(UserCreationForm):
    """
    Formulário personalizado para criação de usuários no admin
    """

    name = forms.CharField(label="Nome", max_length=150, required=True)
    cpf = forms.CharField(max_length=11, required=True)
    cargo = forms.ModelChoiceField(label="Perfil de acesso", queryset=Cargo.objects.all(), required=True)
    rede = forms.ChoiceField(choices=TipoGestaoChoices.choices, required=True, label="Rede")
    is_validado = forms.BooleanField(label="Usuário validado", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'name', 'cpf', 'cargo', 'rede', 'unidades', 'is_validado'
        )

    def clean_cpf(self):
        """Valida o CPF (apenas números)"""
        cpf = self.cleaned_data.get('cpf')
        if cpf and not cpf.isdigit():
            raise ValidationError('CPF deve conter apenas números')
        return cpf


class CustomUserChangeForm(UserChangeForm):
    """
    Formulário personalizado para alteração de usuários no admin
    """

    name = forms.CharField(label="Nome", max_length=150, required=True)
    cpf = forms.CharField(max_length=11, required=True)
    cargo = forms.ModelChoiceField(label="Perfil de acesso", queryset=Cargo.objects.all(), required=True)
    rede = forms.ChoiceField(choices=TipoGestaoChoices.choices, required=True, label="Rede")
    is_validado = forms.BooleanField(label="Usuário validado", required=False)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def clean_cpf(self):
        """Valida o CPF (apenas números)"""
        cpf = self.cleaned_data.get('cpf')
        if cpf and not cpf.isdigit():
            raise ValidationError('CPF deve conter apenas números')
        return cpf


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuração do admin para o modelo User customizado
    """

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    change_password_form = CustomAdminPasswordChangeForm
    # Campos exibidos na lista de usuários
    list_display = ('username', 'name', 'email', 'cargo', 'rede', 'is_validado', 'is_core_sso')
    
    search_fields = ('username', 'name', 'email', 'cpf')
    ordering = ('username',)

    list_filter = ('rede', 'is_validado', 'is_core_sso') # + BaseUserAdmin.list_filter

    # Configuração dos fieldsets (formulário de edição)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Adicionais', {
            'fields': ('name', 'cpf', 'cargo', 'uuid', 'rede', 'unidades', 'is_validado')
        }),
    )
    # Configuração dos fieldsets para criação
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'name', 'cpf', 'cargo', 'rede', 'unidades', 'is_validado', 'password1', 'password2'),
        }),
        ('Permissões', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    # Campos somente leitura
    readonly_fields = ('uuid', 'date_joined', 'last_login')
    autocomplete_fields = ('unidades',)

    def get_readonly_fields(self, request, obj=None):
        """
        Define campos somente leitura baseado no contexto
        """
        readonly_fields = list(self.readonly_fields)
        # Se não é superuser, não pode alterar is_superuser
        if not request.user.is_superuser:
            readonly_fields.append('is_superuser')
        return readonly_fields

    @admin.action(description="Enviar usuários para CoreSSO")
    def enviar_para_core_sso(self, request, queryset):

        if 'confirm' in request.POST:

            queryset_filtrado = queryset.filter(
                rede=TipoGestaoChoices.INDIRETA,
                is_validado=True
            )

            updated = queryset_filtrado.update(is_active=False)
            ignorados = queryset.count() - queryset_filtrado.count()

            self.message_user(
                request,
                f"{updated} usuário(s) registrado(s) com sucesso no CoreSSO!",
                messages.SUCCESS
            )

            if ignorados:
                self.message_user(
                    request,
                    f"Erro no registo de {ignorados} usuário(s). É necessário cumprir todos os requisitos.",
                    messages.ERROR
                )
        
            return None

        request.current_app = self.admin_site.name
        return render(request, "admin/users/user/confirm_enviar_core_sso.html", {
            "queryset": queryset,
            "action": "enviar_para_core_sso",
            "title": "Você confirma o envio dos usuários selecionados para o CoreSSO?",
        })
    
    actions = ["enviar_para_core_sso"]


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    """
    Configuração do admin para o modelo Cargo
    """

    list_display = ('codigo', 'nome')
    search_fields = ('codigo', 'nome')
    ordering = ('codigo',)
    readonly_fields = ('uuid',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('codigo', 'nome', 'uuid')
        }),
    )