from django.urls import path
from . import views

urlpatterns = [
    path("graficas/", views.graficas, name="graficas"),
  
]