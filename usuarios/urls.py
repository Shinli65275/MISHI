from django.urls import path
from . import views

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("crear-empleado/", views.crear_empleado, name="crear_empleado"),
    path("perfil/",views.perfil,name="perfil"),
    path("perfil/password/",   views.cambiar_password, name="cambiar_password"),
    path('empleados/', views.lista_empleados, name='lista_empleados'),
    path('empleados/crear/', views.crear_empleado, name='crear_empleado'),
    path('empleados/eliminar/<int:usuario_negocio_id>/', views.eliminar_empleado, name='eliminar_empleado'),
    path('empleados/editar/<int:usuario_negocio_id>/', views.editar_empleado, name='editar_empleado'),
    path('perfil/ticket/', views.guardar_ticket, name='guardar_ticket'),
    ]
