from datetime import timedelta
from django.db import models
from negocios.models import Negocio
from productos.models import Producto
from proveedores.models import Proveedor
from django.utils import timezone
from usuarios.models import UsuarioNegocio

class Compra(models.Model): # Negocio, Proveedor, Numero factura, Total, Total productos, Fecha
    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)

    numero_factura = models.CharField(max_length=20, unique=True)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_productos = models.PositiveIntegerField(default=0)

    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(UsuarioNegocio, on_delete=models.DO_NOTHING, default=None)   

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            negocio_id = str(self.negocio.id).zfill(2)

            ultima_compra = Compra.objects.filter(
                negocio=self.negocio
            ).order_by("-id").first()

            if ultima_compra:
                ultimo_numero = int(ultima_compra.numero_factura.split("-")[1])
                nuevo_numero = str(ultimo_numero + 1).zfill(4)
            else:
                nuevo_numero = "0001"

            self.numero_factura = f"{negocio_id}-{nuevo_numero}"

        super().save(*args, **kwargs)

class DetalleCompra(models.Model): # Compra, Producto, Cantidad, Precio compra, Subtotal
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles"
    )

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)

    cantidad = models.PositiveIntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)


class Lote(models.Model):
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="lotes"
    )

    lote = models.CharField(max_length=50)
    cantidad = models.PositiveIntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_creacion = models.DateTimeField(default=timezone.now)

    precio_lote = models.DecimalField(max_digits=12, decimal_places=2, blank=True)

    class Meta:
        unique_together = ('lote', 'producto', 'negocio')

    def __str__(self):
        return self.lote
    
    def calcular_precio_lote(self):
        self.precio_lote = self.cantidad * self.precio_compra
        return self.precio_lote

    def save(self, *args, **kwargs):
        self.precio_lote = self.cantidad * self.precio_compra
        letras_producto = self.producto.nombre[:1].upper()
        producto_id = str(self.producto.id).zfill(4)
        negocio_id = str(self.negocio.id).zfill(2)
        fecha_base = self.fecha_creacion or timezone.now()
        hoy = fecha_base.strftime("%y%m%d")

        codigo_generado = f"{letras_producto}{producto_id}N{negocio_id}{hoy}"


        lote_existente = Lote.objects.filter(
            lote=codigo_generado,
            producto=self.producto,
            negocio=self.negocio
        ).first()

        if lote_existente and not self.pk:
            Lote.objects.filter(id=lote_existente.id).update(
                cantidad=lote_existente.cantidad + self.cantidad
            )

            self.producto.stock += self.cantidad
            self.producto.save()

            return  
        else:
            self.lote = codigo_generado
            super().save(*args, **kwargs)

            self.producto.stock += self.cantidad
            self.producto.save()


class Egreso(models.Model):

    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=100)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descripcion} - ${self.monto}"


class EgresoFijo(models.Model):

    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.descripcion} - ${self.monto}"
