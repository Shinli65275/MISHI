from django.contrib import admin
from .models import Ingreso, Venta, DetalleVenta

@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("negocio", "fecha", "concepto","referencia")

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("negocio", "fecha", "total", "total_productos", "usuario")
