import uuid as uuid
from django.db import models
 
class TemNome(models.Model):
    nome = models.CharField('Nome', max_length=160)
 
    class Meta:
        abstract = True
 
class TemCriadoEm(models.Model):
    criado_em = models.DateTimeField("Criado em", editable=False, auto_now_add=True)
 
    class Meta:
        abstract = True
 
class TemAlteradoEm(models.Model):
    alterado_em = models.DateTimeField("Alterado em", editable=False, auto_now=True)
 
    class Meta:
        abstract = True
 
 
class TemChaveExterna(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
 
    @classmethod
    def by_uuid(cls, uuid):
        return cls.objects.get(uuid=uuid)
 
    class Meta:
        abstract = True
 
class ModeloBase(TemChaveExterna, TemCriadoEm, TemAlteradoEm):
    # Expoe explicitamente o model manager para evitar falsos alertas de Unresolved attribute reference for class Model
    objects = models.Manager()
 
    @classmethod
    def get_valores(cls, user=None, associacao_uuid=None):
        return cls.objects.all()
 
    @classmethod
    def by_id(cls, id):
        return cls.objects.get(id=id)
 
    class Meta:
        abstract = True