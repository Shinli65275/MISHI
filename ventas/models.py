from django.db import models
from inventario.models import Producto
from negocios.models import Negocio 
from django.db import transaction

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
    
    def restar_stock(self):
        self.producto.stock -= self.cantidad
        self.producto.save()
    

    def restar_lotes(self):
        cantidad_restante = self.cantidad
        lotes = self.producto.lotes.filter(stock__gt=0).order_by('fecha_vencimiento')

        for lote in lotes:
            if cantidad_restante <= 0:
                break

            if lote.stock >= cantidad_restante:
                lote.stock -= cantidad_restante
                lote.save()
                cantidad_restante = 0
            else:
                cantidad_restante -= lote.stock
                lote.stock = 0
                lote.save()

        if cantidad_restante > 0:
            raise ValueError("No hay suficiente stock en los lotes para completar la venta.")


class Ingreso(models.Model):
    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    concepto = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
