# movimientos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_usuarios, name='movimientos_usuarios'),
    path('usuario/<int:usuario_id>/', views.dias_usuario, name='movimientos_dias'),
    path('usuario/<int:usuario_id>/dia/<str:fecha>/', views.movimientos_dia, name='movimientos_dia'),
    path('venta/detalle/<int:venta_id>/json/',  views.venta_detalle_json,  name='venta_detalle_json'),
    path('compra/detalle/<int:compra_id>/json/', views.compra_detalle_json, name='compra_detalle_json'),

]