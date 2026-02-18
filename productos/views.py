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

    # 🔐 Solo ADMIN puede crear
    if rol != "ADMIN":
        return redirect("lista_productos")
    

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        proveedor_id = request.POST.get("proveedor")
        precio_compra = request.POST.get("precio_compra")
        precio_venta = request.POST.get("precio_venta")
        stock = request.POST.get("stock")
        stock_minimo = request.POST.get("stock_minimo")
        if stock_minimo == "":
            stock_minimo = -1
        stock_maximo = request.POST.get("stock_maximo")
        if stock_maximo == "":
            stock_maximo = -1

        proveedor = Proveedor.objects.get(id=proveedor_id)

        Producto.objects.create(
            negocio=negocio,
            nombre=nombre,
            proveedor=proveedor,
            precio_venta=precio_venta,
            stock=stock,
            stock_minimo=stock_minimo,
            stock_maximo=stock_maximo,
        )
        return redirect("lista_productos") 

    return render(request, "productos/crear_producto.html", {"proveedores": Proveedor.objects.filter(negocio=negocio)})


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