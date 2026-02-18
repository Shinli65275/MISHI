from django.db import models
from inventario.models import Producto
from negocios.models import Negocio  # si lo tienes en otra app

class Venta(models.Model):

    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_productos = models.IntegerField(default=0)

    def __str__(self):
        return f"Venta #{self.id} - ${self.total}"


class DetalleVenta(models.Model):

    venta = models.ForeignKey(
        Venta,
        related_name="detalles",
        on_delete=models.CASCADE
    )

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class Ingreso(models.Model):
    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    concepto = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)