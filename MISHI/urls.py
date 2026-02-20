from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from MISHI.views import CustomLoginView, inicio, logout_view,nada
from inventario.views import lista_egresos,lista_egresos_fijos
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
    path("egresos_fijos/", lista_egresos_fijos, name="egresos_fijos"),
    path("graficas/", include("graficas.urls")),
    path('movimientos/', include('movimientos.urls')),

    path("cotizacion/", nada, name="cotizacion"),
]

