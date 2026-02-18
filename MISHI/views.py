from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count
import json
from datetime import timedelta
from calendar import monthrange

from negocios.utils import get_negocio_activo, get_rol_usuario
from usuarios.models import UsuarioNegocio
from ventas.models import Ingreso, Venta
from inventario.models import Egreso
from inventario.models import Producto


def nada(request):
    return render(request, "cotizacion.html", {})

def logout_view(request):
    logout(request)
    return redirect('login') # Cambia 'login' por tu ruta de inicio

class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)

        user = self.request.user

        relacion = UsuarioNegocio.objects.filter(
            usuario=user,
            activo=True
        ).first()

        if relacion:
            self.request.session["negocio_id"] = relacion.negocio.id
        else:
            self.request.session.pop("negocio_id", None)

        return response





@login_required
def inicio(request):
    negocio = get_negocio_activo(request)
    hoy     = timezone.now()

    inicio_hoy = hoy.replace(hour=0,  minute=0,  second=0,  microsecond=0)
    fin_hoy    = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)
    inicio_ayer = inicio_hoy - timedelta(days=1)
    fin_ayer    = fin_hoy    - timedelta(days=1)

    # ── KPI: ventas hoy ──
    ventas_hoy = Ingreso.objects.filter(
        negocio=negocio, fecha__range=(inicio_hoy, fin_hoy)
    ).aggregate(t=Sum("monto"))["t"] or 0

    ventas_ayer = Ingreso.objects.filter(
        negocio=negocio, fecha__range=(inicio_ayer, fin_ayer)
    ).aggregate(t=Sum("monto"))["t"] or 0

    delta_ventas = 0.0
    if ventas_ayer:
        delta_ventas = round(((float(ventas_hoy) - float(ventas_ayer)) / float(ventas_ayer)) * 100, 1)

    # ── KPI: órdenes hoy ──
    ordenes_hoy = Venta.objects.filter(
        negocio=negocio, fecha__range=(inicio_hoy, fin_hoy)
    ).count()

    # ── KPI: egresos hoy ──
    egresos_hoy = Egreso.objects.filter(
        negocio=negocio, fecha__range=(inicio_hoy, fin_hoy)
    ).aggregate(t=Sum("monto"))["t"] or 0

    # ── KPI: productos / stock bajo ──
    total_productos    = Producto.objects.filter(negocio=negocio).count()
    productos_bajo_stock = Producto.objects.filter(
        negocio=negocio, stock__lte=5   # ajusta el umbral según tu modelo
    ).count()

    # ── Actividad reciente (últimos 10 movimientos: ingresos + egresos) ──
    ingresos_rec = list(
        Ingreso.objects.filter(negocio=negocio)
        .order_by("-fecha")[:10]
        .values("concepto", "monto", "fecha")
    )
    for i in ingresos_rec:
        i["tipo"] = "ing"
        i["tipo_label"] = "Ingreso"

    egresos_rec = list(
        Egreso.objects.filter(negocio=negocio)
        .order_by("-fecha")[:10]
        .values_list("descripcion", "monto", "fecha")
    )
    egresos_rec = [
        {"concepto": d, "monto": m, "fecha": f, "tipo": "egr", "tipo_label": "Egreso"}
        for d, m, f in egresos_rec
    ]

    actividad_reciente = sorted(
        ingresos_rec + egresos_rec,
        key=lambda x: x["fecha"],
        reverse=True
    )[:10]

    # ── Mini gráfica: ingresos últimos 7 días ──
    labels_7d = []
    data_7d   = []
    for i in range(6, -1, -1):
        dia     = hoy - timedelta(days=i)
        ini_dia = dia.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        fin_dia = dia.replace(hour=23, minute=59, second=59, microsecond=999999)
        total   = Ingreso.objects.filter(
            negocio=negocio, fecha__range=(ini_dia, fin_dia)
        ).aggregate(t=Sum("monto"))["t"] or 0
        labels_7d.append(dia.strftime("%d %b").lstrip("0"))   # ej. "18 Feb"
        data_7d.append(float(total))

    # ── Stock bajo (top 5) ──
    MAX_STOCK_REF = 50   # referencia para calcular el % de la barra
    productos_stock = Producto.objects.filter(
        negocio=negocio, stock__lte=20
    ).order_by("stock")[:5]

    stock_bajo = [
        {
            "nombre":    p.nombre,
            "stock":     p.stock,
            "stock_pct": min(int((p.stock / MAX_STOCK_REF) * 100), 100),
        }
        for p in productos_stock
    ]

    # ── Resumen del mes ──
    primer_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ultimo_mes = hoy.replace(
        day=monthrange(hoy.year, hoy.month)[1],
        hour=23, minute=59, second=59, microsecond=999999
    )

    ingresos_mes = Ingreso.objects.filter(
        negocio=negocio, fecha__range=(primer_mes, ultimo_mes)
    ).aggregate(t=Sum("monto"))["t"] or 0

    egresos_mes = Egreso.objects.filter(
        negocio=negocio, fecha__range=(primer_mes, ultimo_mes)
    ).aggregate(t=Sum("monto"))["t"] or 0

    balance_mes = float(ingresos_mes) - float(egresos_mes)

    context = {
        # KPIs
        "ventas_hoy":          ventas_hoy,
        "delta_ventas":        delta_ventas,
        "ordenes_hoy":         ordenes_hoy,
        "egresos_hoy":         egresos_hoy,
        "total_productos":     total_productos,
        "productos_bajo_stock": productos_bajo_stock,
        "fecha_hoy":           hoy.strftime("%d/%m/%Y"),

        # Actividad
        "actividad_reciente":  actividad_reciente,

        # Mini chart
        "labels_7d_json":      json.dumps(labels_7d),
        "data_7d_json":        json.dumps(data_7d),

        # Stock
        "stock_bajo":          stock_bajo,

        # Resumen mes
        "ingresos_mes":        ingresos_mes,
        "egresos_mes":         egresos_mes,
        "balance_mes":         balance_mes,
    }

    return render(request, "inicio.html", context)


