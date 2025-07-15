from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm
 
from .models import User, Cargo

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
    cargo = forms.ModelChoiceField(queryset=Cargo.objects.all(), required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('name', 'cpf', 'cargo')

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
    cargo = forms.ModelChoiceField(queryset=Cargo.objects.all(), required=True)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = UserChangeForm.Meta.fields

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
    list_display = ('username', 'name', 'email', 'cargo')
    search_fields = ('username', 'name', 'email', 'cpf')
    ordering = ('username',)
    # Configuração dos fieldsets (formulário de edição)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Adicionais', {
            'fields': ('name', 'cpf', 'cargo', 'uuid')
        }),
    )
    # Configuração dos fieldsets para criação
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'name', 'cpf', 'cargo', 'password1', 'password2'),
        }),
        ('Permissões', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    # Campos somente leitura
    readonly_fields = ('uuid', 'date_joined', 'last_login')
    def get_readonly_fields(self, request, obj=None):
        """
        Define campos somente leitura baseado no contexto
        """
        readonly_fields = list(self.readonly_fields)
        # Se não é superuser, não pode alterar is_superuser
        if not request.user.is_superuser:
            readonly_fields.append('is_superuser')
        return readonly_fields

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