# movimientos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_usuarios, name='movimientos_usuarios'),
    path('usuario/<int:usuario_id>/', views.dias_usuario, name='movimientos_dias'),
    path('usuario/<int:usuario_id>/dia/<str:fecha>/', views.movimientos_dia, name='movimientos_dia'),
]