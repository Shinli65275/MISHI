from django.urls import path
from . import views

urlpatterns = [
    path("crear/", views.crear_producto, name="crear_producto"),
    path("", views.lista_productos, name="lista_productos"),
    path("editar/<int:producto_id>/", views.editar_producto, name="editar_producto"),
]
