from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from inventario.models import Producto
from django.contrib.auth.decorators import login_required
from negocios.utils import get_negocio_activo
from ventas.models import DetalleVenta, Venta, Ingreso
from django.db import transaction
import json
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib import pagesizes
from io import BytesIO
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

    negocio = get_negocio_activo(request)

    productos = Producto.objects.filter(
        negocio=negocio,
        stock__gt=0
    )

    return render(request, "ventas/nueva_venta.html", {
        "productos": productos
    })


import json
from django.views.decorators.csrf import csrf_exempt

@login_required
@transaction.atomic
def guardar_venta(request):
    negocio = get_negocio_activo(request)

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    # 1) Intentar leer JSON (frontend usa application/json)
    try:
        if request.content_type and "application/json" in request.content_type:
            payload = json.loads(request.body.decode("utf-8") or "{}")
            productos = payload.get("data_venta")
            if productos is None:
                return JsonResponse({"error": "Payload inválido"}, status=400)

            venta = Venta.objects.create(negocio=negocio, total=0)
            total = 0
            total_productos = 0

            for item in productos:
                producto = Producto.objects.get(id=item["id"])

                if producto.stock < item["cantidad"]:
                    return JsonResponse({"error": f"Stock insuficiente de {producto.nombre}"}, status=400)

                subtotal = item["cantidad"] * item["precio"]

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio"],
                    subtotal=subtotal
                )

                producto.stock -= item["cantidad"]
                producto.save()

                total += subtotal
                total_productos += item["cantidad"]

            venta.total = total
            venta.total_productos = total_productos
            venta.save()

            Ingreso.objects.create(
                negocio=negocio,
                concepto=f"Venta #{venta.id}",
                monto=total,
                referencia=f"VENTA-{venta.id}"
            )

            return JsonResponse({"success": True, "venta_id": venta.id})
    except Producto.DoesNotExist:
        return JsonResponse({"error": "Producto no encontrado"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    # 2) Fallback: carrito en sesión (mantener compatibilidad con la otra implementación)
    carrito = request.session.get("carrito", {})
    if not carrito:
        return JsonResponse({"error": "Carrito vacío"}, status=400)

    venta = Venta.objects.create(negocio=negocio, total=0)
    total_venta = 0

    for producto_id, item in carrito.items():
        producto = Producto.objects.get(id=producto_id)

        cantidad = int(item["cantidad"])
        precio = producto.precio_venta
        subtotal = cantidad * precio

        producto.stock -= cantidad
        producto.save()

        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio,
            subtotal=subtotal
        )

        total_venta += subtotal

    venta.total = total_venta
    venta.save()

    Ingreso.objects.create(
        negocio=negocio,
        concepto=f"Venta #{venta.id}",
        monto=total_venta,
        referencia=f"VENTA-{venta.id}"
    )

    request.session["carrito"] = {}
    return redirect("detalle_venta", venta_id=venta.id)


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