from django.db import models
from negocios.models import Negocio
from proveedores.models import Proveedor
from django.db import transaction


class Producto(models.Model): #negocio, nombre, proveedor, precio_venta, stock, codigo, stock_minimo, stock_maximo
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        related_name="productos"
    )

    nombre = models.CharField(max_length=150)
    
    proveedor = models.ForeignKey(
    Proveedor,
    on_delete=models.CASCADE,
    related_name="productos_proveedor"
)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
   
    codigo = models.CharField(max_length=50, blank=True, null=True)

    stock_minimo = models.IntegerField(default=-1)
    stock_maximo = models.IntegerField(default=-1)

    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.negocio.nombre}"

    @property
    def estado_stock(self):
        """Retorna 'agotado', 'bajo', o 'ok' considerando stock_minimo si está definido."""
        if self.stock == 0:
            return "agotado"
        
        
        if self.stock_minimo != -1 and self.stock <= self.stock_minimo:
            return "bajo"
        
        
        if self.stock_minimo == -1 and self.stock <= 10:
            return "bajo"
        
        return "ok"

    @property
    def porcentaje_stock(self):
        """Porcentaje para la barra de progreso."""
        if self.stock == 0:
            return 0
        # Si tiene stock_maximo definido, usarlo
        if self.stock_maximo != -1:
            return min(100, int((self.stock / self.stock_maximo) * 100))
        # Sin stock_maximo, cap en 100 unidades
        return min(100, self.stock)
    


