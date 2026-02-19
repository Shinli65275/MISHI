from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from negocios.utils import get_negocio_activo, get_rol_usuario
from .models import Proveedor


@login_required
def crear_proveedor(request):
    negocio = get_negocio_activo(request)
    rol = get_rol_usuario(request)

    if not negocio:
        return redirect("dashboard")

    # Solo ADMIN puede crear
    if rol != "ADMIN" and rol != "ALMACEN_ADMIN":
        return redirect("lista_proveedores")

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        telefono = request.POST.get("telefono")
        email = request.POST.get("email")
        direccion = request.POST.get("direccion")
        
        proveedor_existente = Proveedor.objects.filter(negocio=negocio, nombre=nombre).first()
        if proveedor_existente:
            messages.error(request, "Ya existe un proveedor con ese nombre en este negocio")
            return render(request, "proveedores/crear_proveedor.html", {
                "nombre": nombre,
                "telefono": telefono,
                "email": email,
                "direccion": direccion
            })
        else:
            Proveedor.objects.create(
                negocio=negocio,
                nombre=nombre,
                telefono=telefono,
                email=email,
                direccion=direccion
            )

            messages.success(request, f"Proveedor '{nombre}' creado exitosamente")
            return redirect("lista_proveedores")
    return render(request, "proveedores/crear_proveedor.html")

@login_required
def lista_proveedores(request):
    negocio = get_negocio_activo(request)

    proveedores = Proveedor.objects.filter(negocio=negocio)

    return render(request, "proveedores/lista_proveedores.html", {
        "proveedores": proveedores
    })


@login_required
def editar_proveedor(request, proveedor_id):
    """Edita un proveedor existente"""
    negocio_id = request.session.get("negocio_id")
    
    if not negocio_id:
        messages.error(request, "No hay un negocio activo seleccionado")
        return redirect('seleccionar_negocio')
    
    proveedor = get_object_or_404(Proveedor, id=proveedor_id, negocio_id=negocio_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        
        if not nombre:
            messages.error(request, "El nombre del proveedor es obligatorio")
            return render(request, 'proveedores/editar_proveedor.html', {'proveedor': proveedor})
        
        try:
            proveedor.nombre = nombre
            proveedor.telefono = telefono
            proveedor.email = email
            proveedor.direccion = direccion
            proveedor.save()
            
            messages.success(request, f"Proveedor '{nombre}' actualizado exitosamente")
            return redirect('lista_proveedores')
            
        except Exception as e:
            messages.error(request, f"Error al actualizar el proveedor: {str(e)}")
    
    return render(request, 'proveedores/editar_proveedor.html', {'proveedor': proveedor})


@login_required
def eliminar_proveedor(request, proveedor_id):
    # Faltaban comillas en la clave de la sesión
    negocio_id = request.session.get('negocio_id') 

    if request.method == 'POST':
        try:
            # Filtramos por id y negocio_id para asegurar que pertenezca al negocio activo
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, negocio_id=negocio_id)
            nombre = proveedor.nombre
            proveedor.delete()
            messages.success(request, f"Proveedor {nombre} eliminado exitosamente")
        except Exception as e:
            messages.error(request, f"Error al eliminar el proveedor: {str(e)}")
            
    return redirect('lista_proveedores') # Siempre redirigir al finalizar
