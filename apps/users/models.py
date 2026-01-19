import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.unidades.models.unidades import Unidade, TipoGestaoChoices


class User(AbstractUser):
    """
    Modelo de usuário customizado do sistema
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    name = models.CharField("Nome", max_length=150)
    cpf = models.CharField("CPF", max_length=11, unique=True)
    email = models.EmailField("E-mail", max_length=254, null=True, blank=True, default="")
    cargo = models.ForeignKey(
        'Cargo',
        on_delete=models.PROTECT,
        default=3085,
        help_text="Cargo do usuário no sistema"
    )
    unidades = models.ManyToManyField(
        Unidade,
        related_name="usuarios",
        blank=True,
        help_text="Unidades associadas ao usuário"
    )
    rede = models.CharField(
        max_length=10,
        choices=TipoGestaoChoices.choices,
        default=TipoGestaoChoices.DIRETA
    )
    is_validado = models.BooleanField("Validado", default=False, help_text="Indica se o usuário foi validado")
    is_core_sso = models.BooleanField("CoreSSO", default=False, help_text="Indica se o usuário possue cadastro no coreSSO")
    
    # mapeamento dos códigos de cargo para facilitar as permissões
    PERFIL_GIPE = 0        # ajuste para o código real no Cargo
    PERFIL_PONTO_FOCAL = 1 # ajuste para o código real
    PERFIL_DIRETOR = 3360     # ajuste para o código real
    
    is_app_admin = models.BooleanField(
        "Administrador GIPE",
        default=False,
        help_text="Indica se o usuário é administrador funcional do GIPE"
    )

    data_aprovacao = models.DateTimeField(
        "Data de Aprovação",
        null=True,
        blank=True,
        help_text="Data e hora em que o usuário foi aprovado"
    )

    responsavel_aprovacao = models.CharField(
        "Responsável pela Aprovação",
        max_length=11,
        null=True,
        blank=True,
        help_text="Codigo responsável pela aprovação"
    )

    data_inativacao = models.DateTimeField(
        "Data de Inativação",
        null=True,
        blank=True,
        help_text="Data e hora em que o usuário foi inativado"
    )

    responsavel_inativacao = models.CharField(
        "Responsável pela Inativação",
        max_length=11,
        null=True,
        blank=True,
        help_text="Codigo responsável pela inativação"
    )

    motivo_inativacao = models.TextField(
        verbose_name="Motivo Inativação",
        help_text="Descrição do motivo da inativação do usuário.",
        blank=True,
    )

    inativado_via_unidade = models.BooleanField(
        "Inativado via unidade",
        default=False,
        help_text="Indica se o usuário foi inativado através da unidade"
    )
                              
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
    
    def __str__(self) -> str:
        return self.username
    
    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save para garantir que a senha seja criptografada
        """

        # Se a senha foi alterada e não está criptografada, criptografa
        if self.password and not self.password.startswith(('pbkdf2_sha256', 'bcrypt', 'argon2')):
            self.set_password(self.password)

        super().save(*args, **kwargs)

    def _has_cargo_code(self, code: int) -> bool:
        return getattr(self.cargo, "codigo", None) == code

    @property
    def is_gipe(self) -> bool:
        return self._has_cargo_code(self.PERFIL_GIPE)

    @property
    def is_ponto_focal(self) -> bool:
        return self._has_cargo_code(self.PERFIL_PONTO_FOCAL)

    @property
    def is_diretor(self) -> bool:
        return self._has_cargo_code(self.PERFIL_DIRETOR)
 

class Cargo(models.Model):
    """
    Modelo para representar cargos disponíveis no sistema
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    codigo = models.IntegerField(unique=True, primary_key=True, help_text="Código único do cargo")
    nome = models.CharField(max_length=100, help_text="Perfil de acesso")

    class Meta:
        verbose_name = "Perfil de Acesso"
        verbose_name_plural = "Perfis de Acesso"
        ordering = ['nome']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"