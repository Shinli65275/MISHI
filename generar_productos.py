import os
import django
from decimal import Decimal

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MISHI.settings")
django.setup()

from productos.models import Producto
from proveedores.models import Proveedor
from negocios.models import Negocio

negocio = Negocio.objects.get(id=1)
proveedores = Proveedor.objects.filter(negocio=negocio)

productos_base = {
    "Sabritas": [
        ("Sabritas Original",     Decimal("9.00"),  Decimal("14.00")),
        ("Sabritas Limón",        Decimal("9.00"),  Decimal("14.00")),
        ("Sabritas Adobadas",     Decimal("9.00"),  Decimal("14.00")),
        ("Doritos Nacho",         Decimal("10.00"), Decimal("16.00")),
        ("Ruffles Queso",         Decimal("10.00"), Decimal("16.00")),
    ],
    "Barcel": [
        ("Takis Fuego",           Decimal("10.50"), Decimal("17.00")),
        ("Takis Blue Heat",       Decimal("10.50"), Decimal("17.00")),
        ("Chips Jalapeño",        Decimal("9.50"),  Decimal("15.00")),
        ("Karameladas",           Decimal("7.00"),  Decimal("12.00")),
        ("Papas Barcel Sal",      Decimal("9.50"),  Decimal("15.00")),
    ],
    "Lala": [
        ("Leche Entera 1L",       Decimal("18.00"), Decimal("24.00")),
        ("Leche Deslactosada 1L", Decimal("20.00"), Decimal("27.00")),
        ("Yoghurt Fresa",         Decimal("14.00"), Decimal("20.00")),
        ("Crema Lala",            Decimal("16.00"), Decimal("22.00")),
        ("Queso Panela",          Decimal("28.00"), Decimal("38.00")),
    ],
    "Alpura": [
        ("Leche Alpura Entera",   Decimal("19.00"), Decimal("25.00")),
        ("Leche Light",           Decimal("20.00"), Decimal("27.00")),
        ("Yoghurt Natural",       Decimal("13.00"), Decimal("19.00")),
        ("Crema Alpura",          Decimal("17.00"), Decimal("23.00")),
        ("Queso Oaxaca",          Decimal("35.00"), Decimal("48.00")),
    ],
    "Bimbo": [
        ("Pan Blanco Grande",     Decimal("22.00"), Decimal("32.00")),
        ("Pan Integral",          Decimal("24.00"), Decimal("34.00")),
        ("Roles Canela",          Decimal("18.00"), Decimal("26.00")),
        ("Donas Azucaradas",      Decimal("16.00"), Decimal("24.00")),
        ("Mantecadas",            Decimal("14.00"), Decimal("20.00")),
    ],
}

contador = 1

for proveedor in proveedores:
    lista_productos = productos_base.get(proveedor.nombre, [])

    for nombre_producto in lista_productos:
        Producto.objects.get_or_create(
            negocio=negocio,
            nombre=nombre_producto[0],
            defaults={
                "proveedor": proveedor,
                "codigo": f"P{contador:04}",
                "precio_venta": nombre_producto[2],
                "precio_compra": nombre_producto[1],
                "stock": 0,
                "stock_minimo": 5,
                "stock_maximo": 50,
            }
        )
        contador += 1

print("Productos generados correctamente 🚀")