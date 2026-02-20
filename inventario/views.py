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
from inventario.models import Compra, DetalleCompra, Egreso, EgresoFijo, Lote
from io import BytesIO
from datetime import date, datetime, timedelta
from django.db import transaction
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib import messages
from negocios.utils import get_negocio_activo
from inventario.models import Producto, Lote   
from django.db.models import Q, F, Sum, Count

from usuarios.models import UsuarioNegocio


@login_required
def nueva_compra(request):
    negocio = get_negocio_activo(request)
    proveedores = Proveedor.objects.filter(negocio=negocio)
    usuario = request.user


    return render(request, "inventario/nueva_compra.html", {
        "proveedores": proveedores
    })

@login_required
def productos_por_proveedor(request, proveedor_id):
    productos = Producto.objects.filter(proveedor_id=proveedor_id)
    data = {
        "productos": [
            {
                "id": p.id,
                "nombre": p.nombre,
                "codigo": p.codigo or "",         
                "precio_compra": float(p.precio_compra)
            }
            for p in productos
        ]
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

    usuario = request.user

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
        proveedor=proveedor,
        usuario=UsuarioNegocio.objects.filter(usuario=usuario, negocio=negocio).first()
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

    request.session['nueva_compra_id'] = compra.id

    messages.success(request, "Compra registrada exitosamente")
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

def lista_compras(request):
    negocio_id = request.session.get('negocio_id')
    
    if not negocio_id:
        return redirect('seleccionar_negocio')
    
    compras = Compra.objects.filter(
        negocio_id=negocio_id
    ).select_related('proveedor')
    
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
            compras = compras.filter(fecha__gte=datetime.strptime(fecha_desde, '%Y-%m-%d'))
        except ValueError:
            pass
    
    compras = compras.order_by('-fecha')
    
    negocio = get_negocio_activo(request)
    proveedores = Proveedor.objects.filter(negocio=negocio)

    # ✅ Sin import local — Compra ya está importada al inicio del archivo
    nueva_compra_id = request.session.pop('nueva_compra_id', None)
    nueva_compra = None
    if nueva_compra_id:
        try:
            nueva_compra = Compra.objects.prefetch_related('detalles__producto').get(id=nueva_compra_id)
        except Compra.DoesNotExist:
            pass

    return render(request, 'inventario/lista_compras.html', {
        'compras': compras,
        'proveedores': proveedores,
        'nueva_compra': nueva_compra,
    })

@login_required
def lista_egresos_fijos(request):

    negocio = get_negocio_activo(request)

    egresos_fijos = EgresoFijo.objects.filter(
        negocio=negocio
    ).order_by("descripcion")

    total_activos   = sum(e.monto for e in egresos_fijos if e.activo)
    total_inactivos = sum(e.monto for e in egresos_fijos if not e.activo)

    return render(request, "inventario/lista_egresos_fijos.html", {
        "egresos_fijos": egresos_fijos,
        "total_activos": total_activos,
        "total_inactivos": total_inactivos,
    })


@login_required
def nuevo_egreso_fijo(request):

    negocio = get_negocio_activo(request)

    # Categorías ya usadas en este negocio para los chips
    categorias_existentes = (
        EgresoFijo.objects.filter(negocio=negocio)
        .values_list("categoria", flat=True)
        .distinct()
        .order_by("categoria")
    )

    if request.method == "POST":
        descripcion = request.POST.get("descripcion", "").strip()
        monto       = request.POST.get("monto")
        categoria   = request.POST.get("categoria", "").strip()
        activo      = request.POST.get("activo") == "on"

        EgresoFijo.objects.create(
            negocio=negocio,
            descripcion=descripcion,
            monto=monto,
            categoria=categoria,
            activo=activo,
        )
        return redirect("egresos_fijos")

    return render(request, "inventario/nuevo_egreso_fijo.html", {
        "categorias_existentes": categorias_existentes,
    })


@login_required
def toggle_egreso_fijo(request, egreso_id):
    """Activa o desactiva un egreso fijo via POST (botón en la lista)."""
    negocio = get_negocio_activo(request)
    egreso  = get_object_or_404(EgresoFijo, id=egreso_id, negocio=negocio)
    egreso.activo = not egreso.activo
    egreso.save()
    return redirect("egresos_fijos")




@login_required
def inventario(request):
    negocio = get_negocio_activo(request)

    q         = request.GET.get("q", "").strip()
    orden     = request.GET.get("orden", "nombre")
    stock_fil = request.GET.get("stock", "todos")

    productos = Producto.objects.filter(negocio=negocio)

    if q:
        productos = productos.filter(nombre__icontains=q)

    # Filtro por nivel de stock
    if stock_fil == "agotado":
        productos = productos.filter(stock=0)
    elif stock_fil == "bajo":
        productos = productos.filter(stock__gt=0).filter(
            Q(stock_minimo__gt=0, stock__lte=F('stock_minimo')) |
            Q(stock_minimo=-1, stock__lte=10)
        )
    elif stock_fil == "ok":
        productos = productos.filter(stock__gt=0).filter(
            Q(stock_minimo__gt=0, stock__gt=F('stock_minimo')) |
            Q(stock_minimo=-1, stock__gt=10)
        )

    orden_map = {
        "nombre":     "nombre",
        "stock_asc":  "stock",
        "stock_desc": "-stock",
        "precio":     "-precio_venta",
    }
    productos = productos.order_by(orden_map.get(orden, "nombre"))

    productos = productos.annotate(
        num_lotes=Count("lotes"),
        valor_inventario=Sum("lotes__precio_compra")
    )

    # ── KPIs ──
    todos           = Producto.objects.filter(negocio=negocio)
    total_productos = todos.count()
    total_stock     = todos.aggregate(t=Sum("stock"))["t"] or 0
    agotados        = todos.filter(stock=0).count()
    bajo_stock      = todos.filter(stock__gt=0).filter(
        Q(stock_minimo__gt=0, stock__lte=F('stock_minimo')) |
        Q(stock_minimo=-1, stock__lte=10)
    ).count()

    lotes_recientes = (
        Lote.objects
        .filter(negocio=negocio)
        .select_related("producto")
        .order_by("-fecha_creacion")[:8]
    )

    context = {
        "productos":       productos,
        "lotes_recientes": lotes_recientes,
        "q":               q,
        "orden":           orden,
        "stock_fil":       stock_fil,
        "total_productos": total_productos,
        "total_stock":     total_stock,
        "bajo_stock":      bajo_stock,
        "agotados":        agotados,
    }

    return render(request, "inventario/inventario.html", context)


@login_required
def detalle_producto(request, producto_id):
    """Vista de lotes de un producto específico."""
    negocio = get_negocio_activo(request)
    producto = get_object_or_404(Producto, id=producto_id, negocio=negocio)
    lotes    = Lote.objects.filter(producto=producto, negocio=negocio).order_by("-fecha_creacion")

    context = {
        "producto": producto,
        "lotes":    lotes,
    }
    return render(request, "inventario/detalle_producto.html", context)