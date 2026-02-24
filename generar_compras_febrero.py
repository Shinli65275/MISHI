import os
import django
from datetime import datetime
from decimal import Decimal
from django.utils import timezone

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MISHI.settings")  # cambia si tu proyecto se llama diferente
django.setup()

from inventario.models import Compra, DetalleCompra, Lote, Egreso
from productos.models import Producto
from proveedores.models import Proveedor
from negocios.models import Negocio
from usuarios.models import UsuarioNegocio

negocio = Negocio.objects.get(id=1)
usuario = UsuarioNegocio.objects.filter(negocio=negocio).first()
productos = Producto.objects.filter(negocio=negocio)

proveedores = Proveedor.objects.filter(negocio=negocio)

for dia in range(1, 28):

    fecha_personalizada = datetime(2026, 2, dia, 10, 0, 0)
    fecha_personalizada = timezone.make_aware(fecha_personalizada)

    for proveedor in proveedores:

        productos = Producto.objects.filter(
            negocio=negocio,
            proveedor=proveedor
        )

        if not productos.exists():
            continue 

        compra = Compra.objects.create(
            negocio=negocio,
            proveedor=proveedor,
            usuario=usuario,
        )

        total = Decimal("0.00")
        total_productos = 0

        for producto in productos:

            cantidad = 5
            precio = producto.precio_compra
            subtotal = cantidad * precio

            
            DetalleCompra.objects.create(
                compra=compra,
                producto=producto,
                cantidad=cantidad,
                precio_compra=precio,
                subtotal=subtotal
            )

            
            Lote.objects.create(
                negocio=negocio,
                producto=producto,
                cantidad=cantidad,
                precio_compra=precio,
                precio_lote=precio * cantidad,
                fecha_creacion=fecha_personalizada
            )


            total += subtotal
            total_productos += cantidad

        compra.total = total
        compra.total_productos = total_productos
        compra.fecha = fecha_personalizada
        compra.save()

        egreso = Egreso.objects.create(
            negocio=negocio,
            descripcion=f"Compra a {proveedor.nombre}",
            monto=total,
            categoria="Compra de Inventario"
        )

        egreso.fecha = fecha_personalizada
        egreso.save()

print("Compras realistas generadas correctamente 🚀")