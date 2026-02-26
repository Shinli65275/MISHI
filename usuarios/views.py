from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from negocios.models import Negocio,ticket
from negocios.utils import get_negocio_activo, get_rol_usuario
from .models import UsuarioNegocio

def registro(request):
    if request.method == "POST":
        # Datos del usuario
        username = request.POST.get("username")

        if User.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya está en uso")
            return redirect("registro")

        password = request.POST.get("password")

        # Datos del negocio
        nombre_negocio = request.POST.get("nombre_negocio")
        if Negocio.objects.filter(nombre=nombre_negocio).exists():
            messages.error(request, "El nombre del negocio ya está en uso")
            return redirect("registro")
        direccion = request.POST.get("direccion")
        telefono = request.POST.get("telefono")

        #Verificar si es distribuidor
        distribuidor = request.POST.get("es_distribuidor")

        user = User.objects.create_user(
            username=username,
            password=password
        )

        negocio = Negocio.objects.create(
            nombre=nombre_negocio,
            direccion=direccion,
            telefono=telefono
        )

        UsuarioNegocio.objects.create(
            usuario=user,
            negocio=negocio,
            rol="ALMACEN_ADMIN" if distribuidor == "si" else "ADMIN"
        )
        
        ticket.objects.create(
            negocio = negocio,
            nombre_negocio = nombre_negocio,
            mensaje = "",
        )



        # Loguear automáticamente
        login(request, user)

        # Guardar negocio activo en sesión
        request.session["negocio_id"] = negocio.id


        return redirect("inicio")

    return render(request, "usuarios/registro.html")

@login_required
def dashboard(request):
    return render(request, "inicio.html")




@login_required
def crear_empleado(request):
    negocio = get_negocio_activo(request)
    rol = get_rol_usuario(request)

    if rol != "ADMIN" and rol != "ALMACEN_ADMIN":
        return redirect("inicio")

    if not negocio:
        return redirect("inicio")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        rol_empleado = request.POST.get("rol")

        if User.objects.filter(username=username).exists():
            messages.error(request, "El usuario ya existe")
            return redirect("crear_empleado")

        user = User.objects.create_user(
            username=username,
            password=password
        )

        UsuarioNegocio.objects.create(
            usuario=user,
            negocio=negocio,
            rol=rol_empleado,
            activo=True
        )

        messages.success(request, "Empleado creado correctamente")
        return redirect("inicio")

    return render(request, "usuarios/crear_empleado.html")




@login_required
def perfil(request):
    negocio = get_negocio_activo(request)
    rol = None
    if negocio:
        try:
            rel = UsuarioNegocio.objects.get(usuario=request.user, negocio=negocio)
            rol = rel.rol
        except UsuarioNegocio.DoesNotExist:
            pass

    ticket_config = None
    if negocio:
        ticket_config, _ = ticket.objects.get_or_create(
            negocio=negocio,
            defaults={
                'nombre_negocio': negocio.nombre,
                'mensaje': 'Gracias por su compra'
            }
        )

    return render(request, "usuarios/perfil.html", {"negocio": negocio, "rol": rol,'ticket_config': ticket_config,})

@login_required
def cambiar_password(request):
    if request.method != "POST":
        return redirect("perfil")

    user         = request.user
    old_password = request.POST.get("old_password", "")
    new_pass1    = request.POST.get("new_password1", "")
    new_pass2    = request.POST.get("new_password2", "")

    if not user.check_password(old_password):
        messages.error(request, "La contraseña actual es incorrecta.")
        return redirect("perfil")

    if new_pass1 != new_pass2:
        messages.error(request, "Las contraseñas nuevas no coinciden.")
        return redirect("perfil")

    if len(new_pass1) < 8:
        messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
        return redirect("perfil")

    user.set_password(new_pass1)
    user.save()
    update_session_auth_hash(request, user)   # mantiene la sesión activa
    messages.success(request, "Contraseña cambiada correctamente.")
    return redirect("perfil")

@login_required
def lista_empleados(request):
    negocio_id = request.session.get("negocio_id")
    
    if not negocio_id:
        messages.error(request, "No hay un negocio activo seleccionado")
        return redirect('seleccionar_negocio')  # Ajusta según tu URL
    
    usuarios = UsuarioNegocio.objects.filter(
        negocio_id=negocio_id,
        activo=True
    ).select_related('usuario', 'negocio').order_by('-id')
    print(request.user.is_authenticated)
    return render(request, 'usuarios/lista_usuarios.html', {
        'usuarios': usuarios
    })

@login_required
def eliminar_empleado(request, usuario_negocio_id):
    """Elimina la relación del empleado con el negocio"""
    negocio_id = request.session.get("negocio_id")

    
    rol = get_rol_usuario(request)
    if rol != 'ADMIN' and rol != 'ALMACEN_ADMIN':
        messages.error(request, "No tienes permisos para realizar esta acción")
        return redirect('lista_empleados')
    
    if request.method == 'POST':
        try:
            usuario_negocio = get_object_or_404(
                UsuarioNegocio,
                id=usuario_negocio_id,
                negocio_id=negocio_id
            )
            
            if usuario_negocio.usuario == request.user:
                messages.error(request, "No puedes eliminarte a ti mismo")
                return redirect('lista_empleados')
            
            username = usuario_negocio.usuario.username
            
            usuario_negocio.usuario.delete()
            
            messages.success(request, f"Empleado {username} eliminado exitosamente")
            
        except Exception as e:
            messages.error(request, f"Error al eliminar el empleado: {str(e)}")
    
    return redirect('lista_empleados')


@login_required
def editar_empleado(request, usuario_negocio_id):
    negocio_id = request.session.get('negocio_id')
    

    rol = get_rol_usuario(request)
    if rol != 'ADMIN' and rol != 'ALMACEN_ADMIN':
        messages.error(request, "No tienes permisos para realizar esta acción")
        return redirect('lista_empleados')
    
    usuario_negocio = get_object_or_404(
        UsuarioNegocio,
        id=usuario_negocio_id,
        negocio_id=negocio_id
    )
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        rol_nuevo = request.POST.get('rol')
        password = request.POST.get('password', '').strip()
        
        try:
            usuario = usuario_negocio.usuario
            usuario.email = email
            
            if password:
                if len(password) < 8:
                    messages.error(request, "La contraseña debe tener al menos 8 caracteres")
                    return render(request, 'usuarios/editar_empleado.html', {'usuario_negocio': usuario_negocio})
                usuario.set_password(password)
            
            usuario.save()
            if usuario == request.user and password:
                update_session_auth_hash(request, usuario)

            usuario_negocio.rol = rol_nuevo
            usuario_negocio.save()
            
            messages.success(request, f"Empleado {usuario.username} actualizado exitosamente")
            return redirect('lista_empleados')
            
        except Exception as e:
            messages.error(request, f"Error al actualizar el empleado: {str(e)}")
    
    return render(request, 'usuarios/editar_empleado.html', {
        'usuario_negocio': usuario_negocio
    })


@login_required
def guardar_ticket(request):
    if request.method != 'POST':
        return redirect('perfil')

    # Solo admins
    if get_rol_usuario(request) != 'ADMIN':   
        messages.error(request, 'No tienes permiso para hacer esto.')
        return redirect('perfil')

    negocio = negocio   = get_negocio_activo(request)
    ticket_config, _ = ticket.objects.get_or_create(negocio=negocio)
    ticket_config.nombre_negocio = request.POST.get('nombre_negocio', '').strip()
    ticket_config.mensaje        = request.POST.get('mensaje', '').strip()
    ticket_config.save()

    messages.success(request, 'Configuración del ticket actualizada.')
    return redirect('perfil')