from django.urls import path
from ventas import views

urlpatterns = [
    path("", views.lista_ventas, name="lista_ventas"),
    path("nueva/", views.nueva_venta, name="nueva_venta"),
    path("guardar/", views.guardar_venta, name="guardar_venta"),
    path("<int:venta_id>/", views.detalle_venta, name="detalle_venta"),
    path("buscar-producto/", views.buscar_producto_codigo, name="buscar_producto_codigo"),
    path("<int:venta_id>/pdf/", views.generar_pdf_venta, name="pdf_venta"),


]
