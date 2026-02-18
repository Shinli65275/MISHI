from django.contrib import admin
from .models import UsuarioNegocio

@admin.register(UsuarioNegocio)
class UsuarioNegocioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "negocio", "rol", "activo")
