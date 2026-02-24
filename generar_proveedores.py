import os
import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MISHI.settings")
django.setup()

from proveedores.models import Proveedor
from negocios.models import Negocio

negocio = Negocio.objects.get(id=1)

proveedores = [
    "Sabritas",
    "Barcel",
    "Lala",
    "Alpura",
    "Bimbo"
]

for nombre in proveedores:
    Proveedor.objects.get_or_create(
        negocio=negocio,
        nombre=nombre,
        defaults={
            "telefono": "5550000000",
            "email": f"contacto@{nombre.lower()}.com",
            "direccion": "México"
        }
    )

print("Proveedores generados correctamente 🚀")