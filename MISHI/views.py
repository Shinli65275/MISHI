from urllib import request, response
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from negocios.utils import get_negocio_activo, get_rol_usuario
from usuarios.models import UsuarioNegocio


def nada(request):
    return redirect(request, "nada.html")



def logout_view(request):
    logout(request)
    return redirect('login') # Cambia 'login' por tu ruta de inicio

class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)

        user = self.request.user

        relacion = UsuarioNegocio.objects.filter(
            usuario=user,
            activo=True
        ).first()

        if relacion:
            self.request.session["negocio_id"] = relacion.negocio.id
        else:
            self.request.session.pop("negocio_id", None)

        return response


def inicio(request):
    negocio = get_negocio_activo(request)
    rol = get_rol_usuario(request)
    print("Usuario:", request.user)
    print("Negocio sesión:", request.session.get("negocio_id"))
    print("Rol:", rol)
    return render(request, "inicio.html")