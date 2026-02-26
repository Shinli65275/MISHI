import json
from io import BytesIO
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors, pagesizes
from negocios.utils import get_negocio_activo
from usuarios.models import UsuarioNegocio
from inventario.models import Lote, Producto
from ventas.models import DetalleVenta, Venta, Ingreso
from negocios.models import ticket

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
    try:
        ticket_config = ticket.objects.get(negocio=negocio) 
    except ticket.DoesNotExist:
        ticket_config = None

    return render(request, "ventas/nueva_venta.html", {
        "productos":      productos,
        "productos_json": productos_json,
        'ticket_nombre':  ticket_config.nombre_negocio if ticket_config else 'MI NEGOCIO',
        'ticket_mensaje': ticket_config.mensaje         if ticket_config else 'Gracias por su compra',
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

            venta           = Venta.objects.create(negocio=negocio, total=0, usuario=UsuarioNegocio.objects.filter(usuario=usuario, negocio=negocio).first())
            total           = 0
            total_productos = 0

            for item in productos:
                producto = Producto.objects.select_for_update().get(id=item["id"], negocio=negocio)
                cantidad = int(item["cantidad"])
                precio   = float(item["precio"])

                if producto.stock < cantidad:
                    raise ValueError(f"Stock insuficiente de '{producto.nombre}'. "
                                     f"Disponible: {producto.stock}, solicitado: {cantidad}.")

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

                    lote.precio_lote = lote.cantidad * lote.precio_compra  # ← nuevo
                    lote.save(update_fields=["cantidad", "precio_lote"])   # ← nuevo

                if restante > 0:
                    raise ValueError(f"No se pudo descontar el stock completo de '{producto.nombre}'.")

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

            venta.total           = total
            venta.total_productos = total_productos
            venta.save()

            Ingreso.objects.create(
                negocio=negocio,
                concepto=f"Venta #{venta.id}",
                monto=total,
                referencia=f"#{negocio.id:02d}-{venta.id:04d}",
                venta=venta
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
    ingresos_qs = (
    Ingreso.objects
    .filter(negocio=negocio)
    .select_related('venta')
    .order_by("-fecha")
    )

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
    
    try:
        ticket_config = ticket.objects.get(negocio=negocio) 
    except ticket.DoesNotExist:
        ticket_config = None


    return render(request, "ventas/lista_ingresos.html", {
        "ingresos": ingresos,
        "total_general": total_general,
        "total_hoy": total_hoy,
        "total_registros": total_registros,
        'ticket_nombre':  ticket_config.nombre_negocio if ticket_config else 'MI NEGOCIO',
        'ticket_mensaje': ticket_config.mensaje         if ticket_config else 'Gracias por su compra',
    })

@login_required
def detalle_ingreso_json(request, ingreso_id):
    negocio = get_negocio_activo(request)
    ingreso = get_object_or_404(Ingreso, id=ingreso_id, negocio=negocio)

    items = []
    if ingreso.venta:
        for d in ingreso.venta.detalles.select_related('producto').all():  # ← detalles
            items.append({
                "nombre":   d.producto.nombre,
                "cantidad": d.cantidad,
                "precio":   float(d.precio_unitario),
                "subtotal": float(d.subtotal),
            })

    return JsonResponse({
        "id":         ingreso.id,
        "concepto":   ingreso.concepto,
        "referencia": ingreso.referencia or "",
        "monto":      float(ingreso.monto),
        "fecha":      ingreso.fecha.strftime("%d/%m/%Y"),
        "hora":       ingreso.fecha.strftime("%H:%M"),
        "items":      items,
    })