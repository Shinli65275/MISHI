import os
import django
import random
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MISHI.settings")
django.setup()

from negocios.models import Negocio
from usuarios.models import UsuarioNegocio
from inventario.models import Lote
from productos.models import Producto
from ventas.models import Venta, DetalleVenta, Ingreso

negocio = Negocio.objects.get(id=1)
usuario = UsuarioNegocio.objects.filter(negocio=negocio).first()

cantidad_productos_por_dia = [3, 5, 2, 4, 6, 3, 5, 2, 4, 3, 6, 2, 5, 4, 3, 6, 2, 5, 3, 4, 6, 2, 3, 5, 4, 6, 3]

cantidades_por_dia = [
    [2, 1, 3],          # dia 1
    [1, 3, 2, 1, 2],    # dia 2
    [3, 2],             # dia 3
    [1, 2, 3, 2],       # dia 4
    [2, 1, 3, 2, 1, 3], # dia 5
    [3, 1, 2],          # dia 6
    [2, 3, 1, 2, 1],    # dia 7
    [1, 3],             # dia 8
    [2, 1, 3, 2],       # dia 9
    [3, 2, 1],          # dia 10
    [1, 2, 3, 1, 2, 3], # dia 11
    [2, 1],             # dia 12
    [3, 1, 2, 2, 1],    # dia 13
    [2, 3, 1, 2],       # dia 14
    [1, 2, 3],          # dia 15
    [3, 1, 2, 1, 2, 3], # dia 16
    [2, 1],             # dia 17
    [1, 3, 2, 2, 1],    # dia 18
    [2, 1, 3],          # dia 19
    [3, 2, 1, 2],       # dia 20
    [1, 2, 3, 1, 2, 3], # dia 21
    [3, 2],             # dia 22
    [2, 1, 3],          # dia 23
    [1, 3, 2, 2, 1],    # dia 24
    [2, 3, 1, 2],       # dia 25
    [1, 2, 3, 1, 2, 3], # dia 26
    [3, 1, 2],          # dia 27
]
numeros2 = [0,2, 1, 3, 2, 1, 3, 2, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3]

for dia in range(1, 28):
    n_productos = cantidad_productos_por_dia[dia - 1]
    cantidades  = cantidades_por_dia[dia - 1]
    todos_productos = list(Producto.objects.filter(negocio=negocio, stock__gt=0).order_by('id'))

    # Hora aleatoria entre 9am y 8pm
    hora   = random.randint(9, 20)
    minuto = random.randint(0, 59)

    fecha_personalizada = datetime(2026, 2, dia, hora, minuto, 0)
    fecha_personalizada = timezone.make_aware(fecha_personalizada)

    # Recargar productos con stock en cada iteración
    todos_productos = list(Producto.objects.filter(negocio=negocio, stock__gt=0))

    inicio  = (dia - 1) * 3 % len(todos_productos)
    indices = [(inicio + i) % len(todos_productos) for i in range(n_productos)]
    muestra = [todos_productos[i] for i in indices]

    with transaction.atomic():

        venta = Venta.objects.create(
        negocio=negocio,
        usuario=usuario,
        total=0,
        total_productos=0,
        fecha=fecha_personalizada  # ← aquí
        )       

        total           = Decimal("0.00")
        total_productos = 0

        for producto in muestra:
            # Refrescar stock real
            producto.refresh_from_db()

            cantidad = numeros2[dia]

            if producto.stock < cantidad:
                continue

            precio   = producto.precio_venta
            subtotal = cantidad * precio

            # FIFO
            lotes = (
                Lote.objects
                .select_for_update()
                .filter(producto=producto, negocio=negocio, cantidad__gt=0)
                .order_by("fecha_creacion")
            )

            restante = cantidad
            for lote in lotes:
                if restante <= 0:
                    break
                if lote.cantidad <= restante:
                    restante      -= lote.cantidad
                    lote.cantidad  = 0
                else:
                    lote.cantidad -= restante
                    restante       = 0

                lote.precio_lote = lote.cantidad * lote.precio_compra 
                lote.save(update_fields=["cantidad", "precio_lote"])  

            if restante > 0:
                continue

            producto.stock -= cantidad
            producto.save(update_fields=["stock"])

            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=subtotal
            )

            total           += subtotal
            total_productos += cantidad

        Venta.objects.filter(id=venta.id).update(
        total=total,
        total_productos=total_productos,
        fecha=fecha_personalizada
    )

        Ingreso.objects.create(
            negocio=negocio,
            concepto=f"Venta #{venta.id}",
            monto=total,
            referencia=f"#{negocio.id:02d}-{venta.id:04d}",
            fecha=fecha_personalizada,
            venta=venta
        )

print("Ventas generadas correctamente 🚀")