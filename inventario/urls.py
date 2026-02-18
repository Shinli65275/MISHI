from django.urls import path
from . import views

urlpatterns = [
    path("nueva/", views.nueva_compra, name="nueva_compra"),
    path("guardar/", views.guardar_compra, name="guardar_compra"),
    path("productos-proveedor/<int:proveedor_id>/", views.productos_por_proveedor),
    path("pdf/<int:compra_id>/", views.generar_pdf, name="generar_pdf"),
    path("compras/", views.lista_compras, name="lista_compras"),
    path("compras/<int:compra_id>/", views.detalle_compra, name="detalle_compra"),
    path("egresos/", views.lista_egresos, name="lista_egresos"),
    path("egresos/nuevo/", views.nuevo_egreso, name="nuevo_egreso"),

]
