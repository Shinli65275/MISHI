import json
from pyexpat.errors import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from negocios.utils import get_negocio_activo
from proveedores.models import Proveedor
from productos.models import Producto
from inventario.models import Compra, DetalleCompra, Egreso, Lote
from io import BytesIO
from datetime import date, datetime, timedelta
from django.db import transaction
from decimal import Decimal


@login_required
def nueva_compra(request):
    negocio = get_negocio_activo(request)

    proveedores = Proveedor.objects.filter(negocio=negocio)

    return render(request, "inventario/nueva_compra.html", {
        "proveedores": proveedores
    })

@login_required
def productos_por_proveedor(request, proveedor_id):
    negocio = get_negocio_activo(request)

    productos = Producto.objects.filter(
        proveedor_id=proveedor_id,
        negocio=negocio
    )

    data = {
        "productos": list(
            productos.values("id", "nombre")
        )
    }

    return JsonResponse(data)

@login_required
@transaction.atomic
def guardar_compra(request):

    if request.method != "POST":
        return redirect("nueva_compra")

    negocio = get_negocio_activo(request)
    if not negocio:
        messages.error(request, "No hay negocio activo")
        return redirect("login")

    proveedor_id = request.POST.get("proveedor")
    data_json = request.POST.get("data_compra")

    if not data_json:
        return redirect("nueva_compra")

    proveedor = get_object_or_404(
        Proveedor,
        id=proveedor_id,
        negocio=negocio
    )

    data = json.loads(data_json)

    compra = Compra.objects.create(
        negocio=negocio,
        proveedor=proveedor
    )

    total = Decimal("0.00")
    total_productos = 0

    for item in data:

        producto = get_object_or_404(
            Producto,
            id=item["id"],
            negocio=negocio
        )

        cantidad = int(item["cantidad"])
        precio = Decimal(item["precio"])
        subtotal = cantidad * precio

        producto.stock += cantidad
        producto.save()

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
            precio_compra=precio
        )

        total += subtotal
        total_productos += cantidad

    compra.total = total
    compra.total_productos = total_productos
    compra.save()

    Egreso.objects.create(
        negocio=negocio,
        descripcion=f"Compra a {proveedor.nombre}",
        monto=total,
        categoria="Compra de Inventario"
    )

    return redirect("lista_compras")

@login_required
def generar_pdf(request, compra_id):
    compra = Compra.objects.get(id=int(compra_id))
    detalles = compra.detalles.all()

    buffer = BytesIO()
    response = HttpResponse(content_type='application/pdf')
    filename = compra.numero_factura if compra.numero_factura else compra.id
    response['Content-Disposition'] = f'attachment; filename="compra_{filename}.pdf"'

    doc = SimpleDocTemplate(buffer)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Factura: {compra.numero_factura}", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Proveedor: {compra.proveedor.nombre}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    data = [["Producto", "Cantidad", "Precio", "Subtotal"]]

    for d in detalles:
        data.append([
            d.producto.nombre,
            str(d.cantidad),
            str(d.precio_compra),
            str(d.subtotal)
        ])

    table = Table(data)
    table.setStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])

    elements.append(table)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Productos: {compra.total_productos}", styles["Normal"]))
    elements.append(Paragraph(f"Total: ${compra.total}", styles["Normal"]))

    doc.build(elements)

    buffer.seek(0)
    response.write(buffer.getvalue())
    buffer.close()

    return response




@login_required
def detalle_compra(request, compra_id):

    negocio = get_negocio_activo(request)

    compra = get_object_or_404(
        Compra,
        id=compra_id,
        negocio=negocio
    )

    detalles = compra.detalles.all()

    return render(request, "inventario/detalle_compra.html", {
        "compra": compra,
        "detalles": detalles
    })

@login_required
def nuevo_egreso(request):

    negocio = get_negocio_activo(request)

    if request.method == "POST":

        descripcion = request.POST.get("descripcion")
        monto = request.POST.get("monto")
        categoria = request.POST.get("categoria")

        Egreso.objects.create(
            negocio=negocio,
            descripcion=descripcion,
            monto=monto,
            categoria=categoria
        )

        return redirect("lista_egresos")

    return render(request, "inventario/nuevo_egreso.html")

@login_required
def lista_egresos(request):

    negocio = get_negocio_activo(request)

    # ── Parámetros de filtro ────────────────────────────────────────────
    hoy = date.today()

    # Si no se pasa fecha_desde, se usa el primer día del mes actual
    fecha_desde_str = request.GET.get("fecha_desde", hoy.strftime("%Y-%m-01"))
    fecha_hasta_str = request.GET.get("fecha_hasta", "")
    categoria_filtro = request.GET.get("categoria", "")

    # Parsear fechas
    try:
        fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        fecha_desde = hoy.replace(day=1)

    try:
        fecha_hasta = datetime.strptime(fecha_hasta_str, "%Y-%m-%d").date() if fecha_hasta_str else None
    except (ValueError, TypeError):
        fecha_hasta = None

    # ── Queryset base ───────────────────────────────────────────────────
    egresos = Egreso.objects.filter(
        negocio=negocio,
        fecha__gte=fecha_desde,
    ).order_by("-fecha")

    if fecha_hasta:
        egresos = egresos.filter(fecha__lte=fecha_hasta)

    if categoria_filtro:
        egresos = egresos.filter(categoria=categoria_filtro)

    # ── Totales ─────────────────────────────────────────────────────────
    total_egresos = sum(e.monto for e in egresos)

    # ── Categorías únicas para el selector ─────────────────────────────
    categorias = (
        Egreso.objects.filter(negocio=negocio)
        .values_list("categoria", flat=True)
        .distinct()
        .order_by("categoria")
    )

    return render(request, "inventario/lista_egresos.html", {
        "egresos": egresos,
        "total_egresos": total_egresos,
        "categorias": categorias,
        # Devolver los valores activos para pre-rellenar el form
        "fecha_desde": fecha_desde_str,
        "fecha_hasta": fecha_hasta_str,
        "categoria_filtro": categoria_filtro,
    })

@login_required
def lista_compras(request):
    negocio_id = request.session.get('negocio_id')
    
    if not negocio_id:
        messages.error(request, "No hay un negocio activo seleccionado")
        return redirect('seleccionar_negocio')
    
    # Obtener todas las compras del negocio
    compras = Compra.objects.filter(
        negocio_id=negocio_id
    ).select_related('proveedor')
    
    # Aplicar filtros
    factura = request.GET.get('factura', '').strip()
    proveedor_id = request.GET.get('proveedor', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    
    if factura:
        compras = compras.filter(numero_factura__icontains=factura)
    
    if proveedor_id:
        compras = compras.filter(proveedor_id=proveedor_id)
    
    if fecha_desde:
        try:
            fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
            compras = compras.filter(fecha__gte=fecha_desde_dt)
        except ValueError:
            pass
    
    # Ordenar por fecha más reciente
    compras = compras.order_by('-fecha')
    
    # Obtener lista de proveedores para el filtro
    negocio = get_negocio_activo(request)
    proveedores = Proveedor.objects.filter(negocio=negocio)

    
    return render(request, 'inventario/lista_compras.html', {
        'compras': compras,
        'proveedores': proveedores,
    })
