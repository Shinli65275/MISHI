from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from negocios.models import Negocio
from negocios.utils import get_negocio_activo, get_rol_usuario
from .models import UsuarioNegocio
from django.contrib.auth import update_session_auth_hash


def registro(request):
    if request.method == "POST":
        # Datos del usuario
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Datos del negocio
        nombre_negocio = request.POST.get("nombre_negocio")
        direccion = request.POST.get("direccion")
        telefono = request.POST.get("telefono")

        # Crear usuario
        user = User.objects.create_user(
            username=username,
            password=password
        )

        # Crear negocio con todos los datos
        negocio = Negocio.objects.create(
            nombre=nombre_negocio,
            direccion=direccion,
            telefono=telefono
        )

        # Asignar como ADMIN
        UsuarioNegocio.objects.create(
            usuario=user,
            negocio=negocio,
            rol="ADMIN"
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

    if rol != "ADMIN":
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
def perfil_usuario(request):
    negocio = get_negocio_activo(request)
    rol = get_rol_usuario(request)
    return render(request, "usuarios/perfil.html", {
        "negocio": negocio,
        "rol": rol
    })

@login_required
def lista_empleados(request):
    negocio_id = request.session.get("negocio_id")
    
    if not negocio_id:
        messages.error(request, "No hay un negocio activo seleccionado")
        return redirect('seleccionar_negocio')  # Ajusta según tu URL
    
    # Obtener todos los usuarios del negocio
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

    
    # Verificar que el usuario que intenta eliminar es administrador
    rol = get_rol_usuario(request)
    if rol != 'ADMIN':
        messages.error(request, "No tienes permisos para realizar esta acción")
        return redirect('lista_empleados')
    
    if request.method == 'POST':
        try:
            # Obtener la relación usuario-negocio
            usuario_negocio = get_object_or_404(
                UsuarioNegocio,
                id=usuario_negocio_id,
                negocio_id=negocio_id
            )
            
            # Prevenir que el usuario se elimine a sí mismo
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
    

    # Verificar que el usuario que intenta editar es administrador
    rol = get_rol_usuario(request)
    if rol != 'ADMIN':
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
            # Actualizar información del usuario
            usuario = usuario_negocio.usuario
            usuario.email = email
            
            # Cambiar contraseña solo si se proporcionó una nueva
            if password:
                if len(password) < 8:
                    messages.error(request, "La contraseña debe tener al menos 8 caracteres")
                    return render(request, 'usuarios/editar_empleado.html', {'usuario_negocio': usuario_negocio})
                usuario.set_password(password)
            
            usuario.save()
            if usuario == request.user and password:
                update_session_auth_hash(request, usuario)

            # Actualizar rol
            usuario_negocio.rol = rol_nuevo
            usuario_negocio.save()
            
            messages.success(request, f"Empleado {usuario.username} actualizado exitosamente")
            return redirect('lista_empleados')
            
        except Exception as e:
            messages.error(request, f"Error al actualizar el empleado: {str(e)}")
    
    return render(request, 'usuarios/editar_empleado.html', {
        'usuario_negocio': usuario_negocio
    })