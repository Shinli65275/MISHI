from .models import UsuarioNegocio

def rol_usuario_context(request):
    rol = None
    
    if request.user.is_authenticated:
        negocio_id = request.session.get("negocio_id")
        
        if negocio_id:
            relacion = UsuarioNegocio.objects.filter(
                usuario=request.user,
                negocio_id=negocio_id
            ).first()
            
            if relacion:
                rol = relacion.rol
    
    return {
        'rol_usuario': rol
    }