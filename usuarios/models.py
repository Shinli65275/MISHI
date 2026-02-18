from django.db import models
from django.contrib.auth.models import User

from django.db import models
from django.contrib.auth.models import User
from negocios.models import Negocio


class UsuarioNegocio(models.Model):

    ROLES = [
        ('ADMIN', 'Administrador'),
        ('VENDEDOR', 'Vendedor'),
        ('ALMACEN', 'Almacén'),
        ('ALMACEN_ADMIN', 'Almacén-Admin'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROLES)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.negocio.nombre} ({self.rol})"
