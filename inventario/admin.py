from django.contrib import admin

from django.contrib import admin
from .models import Compra,DetalleCompra, Lote

admin.site.register(Compra)
admin.site.register(DetalleCompra)
admin.site.register(Lote)