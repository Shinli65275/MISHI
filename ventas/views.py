from datetime import date, datetime
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from inventario.models import Lote, Producto
from django.contrib.auth.decorators import login_required
from negocios.utils import get_negocio_activo
from usuarios.models import UsuarioNegocio
from ventas.models import DetalleVenta, Venta, Ingreso
from django.db import transaction
import json
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib import pagesizes
from io import BytesIO
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.utils import timezone

def buscar_producto_codigo(request):

    codigo = request.GET.get("codigo")

    try:
        producto = Producto.objects.get(codigo=codigo)

        return JsonResponse({
            "id": producto.id,
            "nombre": producto.nombre,
            "precio": float(producto.precio_venta),
            "stock": producto.stock
        })

    except Producto.DoesNotExist:
        return JsonResponse({"error": "Producto no encontrado"}, status=404)


@login_required
def nueva_venta(request):
    negocio   = get_negocio_activo(request)
    productos = Producto.objects.filter(negocio=negocio, stock__gt=0)

    productos_json = json.dumps([
        {
            "id":     p.id,
            "nombre": p.nombre,
            "precio": float(p.precio_venta),
            "stock":  p.stock or 0,
            "codigo": p.codigo or ""
        }
        for p in productos
    ])

    return render(request, "ventas/nueva_venta.html", {
        "productos":      productos,
        "productos_json": productos_json,
    })


import json
from django.views.decorators.csrf import csrf_exempt

@login_required
@transaction.atomic
def guardar_venta(request):
    negocio = get_negocio_activo(request)
    usuario = request.user
    print("Usuario que realiza la venta:", usuario.username)
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        if request.content_type and "application/json" in request.content_type:
            payload   = json.loads(request.body.decode("utf-8") or "{}")
            productos = payload.get("data_venta")
            if productos is None:
                return JsonResponse({"error": "Payload inválido"}, status=400)

            venta            = Venta.objects.create(negocio=negocio, total=0,usuario=UsuarioNegocio.objects.filter(usuario=usuario, negocio=negocio).first())
            total            = 0
            total_productos  = 0

            for item in productos:
                producto  = Producto.objects.select_for_update().get(id=item["id"], negocio=negocio)
                cantidad  = int(item["cantidad"])
                precio    = float(item["precio"])

                # ── Verificar stock global antes de operar ──
                if producto.stock < cantidad:
                    raise ValueError(f"Stock insuficiente de '{producto.nombre}'. "
                                     f"Disponible: {producto.stock}, solicitado: {cantidad}.")

                # ── Descontar lotes FIFO (más antiguo primero) ──
                lotes = (
                    Lote.objects
                    .select_for_update()
                    .filter(producto=producto, negocio=negocio, cantidad__gt=0)
                    .order_by("fecha_creacion")   # ← FIFO
                )

                restante = cantidad
                for lote in lotes:
                    if restante <= 0:
                        break

                    if lote.cantidad <= restante:
                        # Este lote se agota por completo
                        restante       -= lote.cantidad
                        lote.cantidad   = 0
                    else:
                        # Este lote cubre el resto
                        lote.cantidad  -= restante
                        restante        = 0

                    lote.save(update_fields=["cantidad"])

                if restante > 0:
                    # Nunca debería llegar aquí si stock global está bien
                    raise ValueError(f"No se pudo descontar el stock completo de '{producto.nombre}'.")

                # ── Actualizar stock global del producto ──
                producto.stock -= cantidad
                producto.save(update_fields=["stock"])

                subtotal = cantidad * precio
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal
                )

                total           += subtotal
                total_productos += cantidad

            venta.total            = total
            venta.total_productos  = total_productos
            venta.save()

            Ingreso.objects.create(
                negocio=negocio,
                concepto=f"Venta #{venta.id}",
                monto=total,
                referencia=f"#{negocio.id:02d}-{venta.id:04d}"
            )

            return JsonResponse({"success": True, "venta_id": venta.id})

    except Producto.DoesNotExist:
        return JsonResponse({"error": "Producto no encontrado"}, status=404)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Solicitud inválida"}, status=400)


@login_required
def lista_ventas(request):

    negocio = get_negocio_activo(request)

    ventas = Venta.objects.filter(
        negocio=negocio
    ).order_by("-id")

    return render(request, "ventas/lista_ventas.html", {
        "ventas": ventas
    })


@login_required
def detalle_venta(request, venta_id):

    negocio = get_negocio_activo(request)

    venta = get_object_or_404(
        Venta,
        id=venta_id,
        negocio=negocio
    )

    detalles = venta.detalles.all()

    return render(request, "ventas/detalle_venta.html", {
        "venta": venta,
        "detalles": detalles
    })


def generar_pdf_venta(request, venta_id):
    venta = Venta.objects.get(id=venta_id)
    detalles = venta.detalles.all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=pagesizes.A4)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Venta #{venta.id}", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    data = [["Producto", "Cantidad", "Precio", "Subtotal"]]

    for detalle in detalles:
        data.append([
            detalle.producto.nombre,
            str(detalle.cantidad),
            f"${detalle.precio}",
            f"${detalle.subtotal}"
        ])

    data.append(["", "", "TOTAL", f"${venta.total}"])

    tabla = Table(data)
    tabla.setStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])

    elements.append(tabla)

    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')





@login_required
def lista_ingresos(request):
    negocio = get_negocio_activo(request)
    ingresos_qs = Ingreso.objects.filter(negocio=negocio).order_by("-fecha")

    # Filtros
    q = request.GET.get("q", "").strip().upper()
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    if q:
        ingresos_qs = ingresos_qs.filter(
            Q(concepto__icontains=q) | Q(referencia__icontains=q)
        )
    if fecha_desde:
        ingresos_qs = ingresos_qs.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        ingresos_qs = ingresos_qs.filter(fecha__date__lte=fecha_hasta)

    # Stats
    total_general = Ingreso.objects.filter(negocio=negocio).aggregate(t=Sum("monto"))["t"] or 0
    total_hoy = Ingreso.objects.filter(
        negocio=negocio, fecha__date=timezone.now().date()
    ).aggregate(t=Sum("monto"))["t"] or 0
    total_registros = Ingreso.objects.filter(negocio=negocio).count()

    # Paginación
    paginator = Paginator(ingresos_qs, 20)
    page = request.GET.get("page", 1)
    ingresos = paginator.get_page(page)

    return render(request, "ventas/lista_ingresos.html", {
        "ingresos": ingresos,
        "total_general": total_general,
        "total_hoy": total_hoy,
        "total_registros": total_registros,
    })