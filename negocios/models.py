from django.db import models
from django.db import models

class Negocio(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class ticket(models.Model):
    negocio    = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    nombre_negocio = models.CharField(max_length=100)
    mensaje = models.CharField(max_length=100)
    def __str__(self):
        return f"Ticket – {self.negocio.nombre}"