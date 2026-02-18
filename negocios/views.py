from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Negocio
from usuarios.models import UsuarioNegocio


@login_required
def crear_negocio(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        direccion = request.POST.get("direccion")
        telefono = request.POST.get("telefono")

        negocio = Negocio.objects.create(
            nombre=nombre,
            direccion=direccion,
            telefono=telefono
        )

        UsuarioNegocio.objects.create(
            usuario=request.user,
            negocio=negocio,
            rol="ADMIN"
        )

        request.session["negocio_id"] = negocio.id

        return redirect("dashboard")

    return render(request, "crear_negocio.html")

