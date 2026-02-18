from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
import json
from datetime import timedelta
from calendar import monthrange

from negocios.utils import get_negocio_activo
from ventas.models import Ingreso, Venta
from inventario.models import Egreso  


@login_required
def graficas(request):
    negocio = get_negocio_activo(request)
    hoy     = timezone.now()

    MESES_ES = [
        "Enero","Febrero","Marzo","Abril","Mayo","Junio",
        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
    ]
    MESES_CORTO = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]

    # ── Periodo seleccionado ──
    try:
        anio = int(request.GET.get("anio", hoy.year))
        mes  = int(request.GET.get("mes",  hoy.month))
        if not (1 <= mes <= 12):
            mes = hoy.month
    except (ValueError, TypeError):
        anio, mes = hoy.year, hoy.month

    primer_dia = hoy.replace(year=anio, month=mes, day=1,
                             hour=0, minute=0, second=0, microsecond=0)
    ultimo_dia = hoy.replace(year=anio, month=mes,
                             day=monthrange(anio, mes)[1],
                             hour=23, minute=59, second=59, microsecond=999999)

    dias_mes = monthrange(anio, mes)[1]
    labels   = [str(d) for d in range(1, dias_mes + 1)]

    # ─────────────────────────────────────────
    # INGRESOS día a día  (campo: fecha)
    # ─────────────────────────────────────────
    ingresos_por_dia = (
        Ingreso.objects
        .filter(negocio=negocio, fecha__range=(primer_dia, ultimo_dia))
        .annotate(dia=TruncDay("fecha"))
        .values("dia")
        .annotate(total=Sum("monto"))
        .order_by("dia")
    )
    ing_map       = {e["dia"].day: float(e["total"]) for e in ingresos_por_dia}
    data_ingresos = [ing_map.get(d, 0) for d in range(1, dias_mes + 1)]

    # ─────────────────────────────────────────
    # EGRESOS día a día  (campo: fecha)
    # ─────────────────────────────────────────
    egresos_por_dia = (
        Egreso.objects
        .filter(negocio=negocio, fecha__range=(primer_dia, ultimo_dia))
        .annotate(dia=TruncDay("fecha"))
        .values("dia")
        .annotate(total=Sum("monto"))
        .order_by("dia")
    )
    egr_map      = {e["dia"].day: float(e["total"]) for e in egresos_por_dia}
    data_egresos = [egr_map.get(d, 0) for d in range(1, dias_mes + 1)]

    # ─────────────────────────────────────────
    # TENDENCIA 6 MESES
    # ─────────────────────────────────────────
    labels_6m   = []
    data_ing_6m = []
    data_egr_6m = []

    for i in range(5, -1, -1):
        m = mes - i
        a = anio
        while m <= 0:
            m += 12
            a -= 1

        p = hoy.replace(year=a, month=m, day=1,
                        hour=0, minute=0, second=0, microsecond=0)
        u = hoy.replace(year=a, month=m,
                        day=monthrange(a, m)[1],
                        hour=23, minute=59, second=59, microsecond=999999)

        ing_mes = Ingreso.objects.filter(
            negocio=negocio, fecha__range=(p, u)
        ).aggregate(t=Sum("monto"))["t"] or 0

        egr_mes = Egreso.objects.filter(
            negocio=negocio, fecha__range=(p, u)
        ).aggregate(t=Sum("monto"))["t"] or 0

        labels_6m.append(MESES_CORTO[m - 1])
        data_ing_6m.append(float(ing_mes))
        data_egr_6m.append(float(egr_mes))

    # ─────────────────────────────────────────
    # REPORTE DEL MES
    # ─────────────────────────────────────────
    total_ingresos_mes = sum(data_ingresos)
    total_egresos_mes  = sum(data_egresos)
    balance_mes        = total_ingresos_mes - total_egresos_mes

    num_ventas_mes = Venta.objects.filter(
        negocio=negocio,
        fecha__range=(primer_dia, ultimo_dia)
    ).count()

    ticket_promedio = (total_ingresos_mes / num_ventas_mes) if num_ventas_mes else 0

    # ── Variación ingresos vs mes anterior ──
    mes_ant  = mes - 1 if mes > 1 else 12
    anio_ant = anio    if mes > 1 else anio - 1

    p_ant = hoy.replace(year=anio_ant, month=mes_ant, day=1,
                        hour=0, minute=0, second=0, microsecond=0)
    u_ant = hoy.replace(year=anio_ant, month=mes_ant,
                        day=monthrange(anio_ant, mes_ant)[1],
                        hour=23, minute=59, second=59)

    ing_ant = Ingreso.objects.filter(
        negocio=negocio, fecha__range=(p_ant, u_ant)
    ).aggregate(t=Sum("monto"))["t"] or 0

    variacion_ingresos = 0.0
    if ing_ant:
        variacion_ingresos = round(
            ((total_ingresos_mes - float(ing_ant)) / float(ing_ant)) * 100, 1
        )

    # ── Top 5 conceptos de ingreso ──
    top_conceptos = list(
        Ingreso.objects
        .filter(negocio=negocio, fecha__range=(primer_dia, ultimo_dia))
        .values("concepto")
        .annotate(total=Sum("monto"))
        .order_by("-total")[:5]
    )

    # ── Top 5 categorías de egreso ──
    top_categorias = list(
        Egreso.objects
        .filter(negocio=negocio, fecha__range=(primer_dia, ultimo_dia))
        .values("categoria")
        .annotate(total=Sum("monto"))
        .order_by("-total")[:5]
    )

    # ── Años disponibles ──
    primer_ingreso = (
        Ingreso.objects.filter(negocio=negocio).order_by("fecha").first()
    )
    anio_inicio       = primer_ingreso.fecha.year if primer_ingreso else hoy.year
    anios_disponibles = list(range(anio_inicio, hoy.year + 1))

    context = {
        "mes_actual":          mes,
        "anio_actual":         anio,
        "anios_disponibles":   anios_disponibles,
        "nombre_mes":          MESES_ES[mes - 1],

        "labels_json":         json.dumps(labels),
        "data_ingresos_json":  json.dumps(data_ingresos),
        "data_egresos_json":   json.dumps(data_egresos),
        "labels_6m_json":      json.dumps(labels_6m),
        "data_ing_6m_json":    json.dumps(data_ing_6m),
        "data_egr_6m_json":    json.dumps(data_egr_6m),

        "total_ingresos_mes":  total_ingresos_mes,
        "total_egresos_mes":   total_egresos_mes,
        "balance_mes":         balance_mes,
        "num_ventas_mes":      num_ventas_mes,
        "ticket_promedio":     ticket_promedio,
        "variacion_ingresos":  variacion_ingresos,
        "top_conceptos":       top_conceptos,
        "top_categorias":      top_categorias,
    }

    return render(request, "reportes/graficas.html", context)