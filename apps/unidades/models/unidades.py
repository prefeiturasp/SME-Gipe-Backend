from django.db import models
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from apps.models_abstracts import ModeloBase, TemNome


class TipoUnidadeChoices(models.TextChoices):
    ADM = 'ADM', 'ADM'
    DRE = 'DRE', 'DRE'
    IFSP = 'IFSP', 'IFSP'
    CMCT = 'CMCT', 'CMCT'
    CECI = 'CECI', 'CECI'
    CEI = 'CEI', 'CEI'
    CEMEI = 'CEMEI', 'CEMEI'
    CIEJA = 'CIEJA', 'CIEJA'
    EMEBS = 'EMEBS', 'EMEBS'
    EMEF = 'EMEF', 'EMEF'
    EMEFM = 'EMEFM', 'EMEFM'
    EMEI = 'EMEI', 'EMEI'
    CEU = 'CEU', 'CEU'
    CEU_CEI = 'CEU CEI', 'CEU CEI'
    CEU_EMEF = 'CEU EMEF', 'CEU EMEF'
    CEU_EMEI = 'CEU EMEI', 'CEU EMEI'
    CEU_CEMEI = 'CEU CEMEI', 'CEU CEMEI'
    CEI_DIRET = 'CEI DIRET', 'CEI DIRET'


class TipoGestaoChoices(models.TextChoices):
    DIRETA = 'DIRETA', 'Direta'
    INDIRETA = 'INDIRETA', 'Indireta ou parceira'


class DresManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(tipo_unidade=TipoUnidadeChoices.DRE)


class Unidade(ModeloBase, TemNome):
    tipo_unidade = models.CharField(
        max_length=10,
        choices=TipoUnidadeChoices.choices,
        default=TipoUnidadeChoices.ADM
    )
    rede = models.CharField(
        max_length=10,
        choices=TipoGestaoChoices.choices,
        default=TipoGestaoChoices.DIRETA
    )
    codigo_eol = models.CharField(
        max_length=6,
        validators=[MinLengthValidator(6)],
        primary_key=True,
        unique=True
    )
    dre = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='unidades_da_dre',
        to_field='codigo_eol',
        blank=True,
        null=True,
        limit_choices_to={'tipo_unidade': TipoUnidadeChoices.DRE}
    )
    sigla = models.CharField(
        max_length=4,
        blank=True,
        default=''
    )

    # Managers
    objects = models.Manager()
    dres = DresManager()

    def clean(self):
        super().clean()
        if self.tipo_unidade == TipoUnidadeChoices.DRE and self.dre is not None:
            raise ValidationError("Unidades do tipo DRE não devem referenciar outra DRE.")
        if self.dre and self.dre.tipo_unidade != TipoUnidadeChoices.DRE:
            raise ValidationError("A unidade associada como DRE deve ser do tipo DRE.")

    def __str__(self):
        return f"{self.nome} ({self.codigo_eol})"