from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from MISHI.views import CustomLoginView, inicio, logout_view,nada
from inventario.views import lista_egresos
urlpatterns = [
    path("", inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("", include("usuarios.urls")),
    path("negocios/", include("negocios.urls")),
    path("productos/", include("productos.urls")),
    path("proveedores/", include("proveedores.urls")),
    path("inventario/", include("inventario.urls")),
    path("ventas/", include("ventas.urls")),
    path("egresos/", lista_egresos, name="egresos"),



    
    path("movimientos/", nada, name="movimientos"),
    path("existencias/", nada, name="existencias"),
    path("ingresos/", nada, name="ingresos"),
    path("reporegresos_fijostes/", nada, name="egresos_fijos"),
    path("cotizacion/", nada, name="cotizacion"),
    path("graficas/", nada, name="graficas"),


]

