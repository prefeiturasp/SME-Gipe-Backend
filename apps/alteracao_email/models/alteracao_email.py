import uuid
from django.db import models
from django.conf import settings

class AlteracaoEmail(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    novo_email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ja_usado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario.username} -> {self.novo_email}"