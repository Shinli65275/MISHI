from .models import Negocio
from usuarios.models import UsuarioNegocio

def get_negocio_activo(request):
    negocio_id = request.session.get("negocio_id")

    if negocio_id:
        try:
            return Negocio.objects.filter(id=negocio_id).first()
        except Negocio.DoesNotExist:
            return None

    return None


def get_rol_usuario(request):
    negocio_id = request.session.get("negocio_id")

    if not negocio_id:
        return None

    relacion = UsuarioNegocio.objects.filter(
        usuario=request.user,
        negocio_id=negocio_id
    ).first()

    if relacion:
        return relacion.rol

    return None
