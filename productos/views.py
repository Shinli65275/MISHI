from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from proveedores.models import Proveedor
from .models import Producto
from negocios.utils import get_negocio_activo, get_rol_usuario


@login_required
def crear_producto(request):
    negocio = get_negocio_activo(request)
    rol = get_rol_usuario(request)

    if not negocio:
        return redirect("dashboard")

    if rol != "ADMIN":
        return redirect("lista_productos")

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        codigo = request.POST.get("codigo")
        proveedor_id = request.POST.get("proveedor")

        precio_venta = float(request.POST.get("precio_venta"))
        precio_compra = float(request.POST.get("precio_compra"))

        stock_minimo = request.POST.get("stock_minimo")
        stock_minimo = int(stock_minimo) if stock_minimo else -1

        stock_maximo = request.POST.get("stock_maximo")
        stock_maximo = int(stock_maximo) if stock_maximo else -1

        proveedor = get_object_or_404(
            Proveedor,
            id=proveedor_id,
            negocio=negocio
        )

        Producto.objects.create( 
            negocio=negocio,
            nombre=nombre,
            codigo=codigo,
            proveedor=proveedor,
            precio_venta=precio_venta,
            precio_compra=precio_compra,
            stock=0,
            stock_minimo=stock_minimo,
            stock_maximo=stock_maximo,
        )

        return redirect("lista_productos")

    proveedores = Proveedor.objects.filter(negocio=negocio)
    return render(request, "productos/crear_producto.html", {
        "proveedores": proveedores
    })



@login_required
def lista_productos(request):
    negocio = get_negocio_activo(request)
    rol = get_rol_usuario(request)

    productos = Producto.objects.filter(negocio=negocio)

    return render(request, "productos/lista_productos.html", {
        "productos": productos,
        "rol": rol
    })


@login_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    proveedores = Proveedor.objects.filter(negocio=get_negocio_activo(request))

    if request.method == "POST":
        producto.nombre       = request.POST.get("nombre")
        producto.codigo       = request.POST.get("codigo")
        producto.precio_venta = request.POST.get("precio_venta")
        proveedor_id          = request.POST.get("proveedor")
        producto.proveedor    = Proveedor.objects.get(id=proveedor_id) if proveedor_id else None
        producto.save()
        return redirect("lista_productos")

    return render(request, "productos/editar_producto.html", {
        "producto": producto,
        "proveedores": proveedores,
    })