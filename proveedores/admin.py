from django.contrib import admin

from .models import Proveedor
@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("negocio","nombre", "telefono", "email", "direccion"  )
