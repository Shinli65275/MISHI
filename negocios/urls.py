from django.urls import path
from . import views

urlpatterns = [
    path("crear/", views.crear_negocio, name="crear_negocio"),
]
