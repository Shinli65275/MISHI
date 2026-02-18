from django.contrib import admin
from .models import Producto

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio_venta", "precio_compra", "stock")
    search_fields = ("nombre", "descripcion")
    list_filter = ("precio_venta", "precio_compra")