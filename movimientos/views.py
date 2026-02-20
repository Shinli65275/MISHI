# movimientos/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from ventas.models import Venta
from inventario.models import Compra
from usuarios.models import UsuarioNegocio
from datetime import datetime


def lista_usuarios(request):
    import unicodedata

    def normalizar(texto):
        return ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        ).lower()

    negocio = request.user.usuarionegocio_set.filter(activo=True).first().negocio
    q = request.GET.get('q', '').strip()

    usuarios = UsuarioNegocio.objects.filter(
        negocio=negocio,
        activo=True
    ).select_related('usuario')

    # Filtro con normalización en Python (por si la BD no soporta unaccent)
    if q:
        q_norm = normalizar(q)
        usuarios = [
            u for u in usuarios
            if q_norm in normalizar(u.usuario.get_full_name() or '')
            or q_norm in normalizar(u.usuario.username or '')
            or q_norm in normalizar(u.usuario.email or '')
        ]

    for u in usuarios:
        u.num_ventas  = Venta.objects.filter(usuario=u).count()
        u.num_compras = Compra.objects.filter(usuario=u).count()
        u.total_movimientos = u.num_ventas + u.num_compras

    return render(request, 'movimientos/lista_usuarios.html', {
        'usuarios': usuarios,
        'total_usuarios': len(usuarios),
        'total_ventas':  sum(u.num_ventas  for u in usuarios),
        'total_compras': sum(u.num_compras for u in usuarios),
        'q': q,
    })


def dias_usuario(request, usuario_id):
    negocio = request.user.usuarionegocio_set.filter(activo=True).first().negocio
    usuario = get_object_or_404(UsuarioNegocio, id=usuario_id, negocio=negocio)

    fecha_filtro = request.GET.get('fecha', '').strip()

    ventas_qs  = Venta.objects.filter(usuario=usuario)
    compras_qs = Compra.objects.filter(usuario=usuario)

    if fecha_filtro:
        ventas_qs  = ventas_qs.filter(fecha__date=fecha_filtro)
        compras_qs = compras_qs.filter(fecha__date=fecha_filtro)

    ventas_por_dia = (
        ventas_qs.annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(total_monto=Sum('total'), cantidad=Count('id'))
        .order_by('-dia')
    )
    compras_por_dia = (
        compras_qs.annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(total_monto=Sum('total'), cantidad=Count('id'))
        .order_by('-dia')
    )

    dias = {}
    for v in ventas_por_dia:
        dia = v['dia']
        if dia not in dias:
            dias[dia] = {'dia': dia, 'ventas': 0, 'compras': 0, 'monto_ventas': 0, 'monto_compras': 0}
        dias[dia]['ventas']       = v['cantidad']
        dias[dia]['monto_ventas'] = v['total_monto']
    for c in compras_por_dia:
        dia = c['dia']
        if dia not in dias:
            dias[dia] = {'dia': dia, 'ventas': 0, 'compras': 0, 'monto_ventas': 0, 'monto_compras': 0}
        dias[dia]['compras']       = c['cantidad']
        dias[dia]['monto_compras'] = c['total_monto']

    dias_lista = sorted(dias.values(), key=lambda x: x['dia'], reverse=True)

    return render(request, 'movimientos/dias_usuario.html', {
        'usuario':             usuario,
        'dias':                dias_lista,
        'total_ventas_count':  sum(d['ventas']  for d in dias_lista),
        'total_compras_count': sum(d['compras'] for d in dias_lista),
        'total_monto_ventas':  sum(d['monto_ventas'] or 0 for d in dias_lista),
        'fecha_filtro':        fecha_filtro,
    })


def movimientos_dia(request, usuario_id, fecha):
    """Muestra todos los movimientos (ventas y compras) de un usuario en un día específico."""
    negocio = request.user.usuarionegocio_set.filter(activo=True).first().negocio
    usuario = get_object_or_404(UsuarioNegocio, id=usuario_id, negocio=negocio)

    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()

    ventas = Venta.objects.filter(
        usuario=usuario,
        fecha__date=fecha_dt
    ).order_by('-fecha')

    compras = Compra.objects.filter(
        usuario=usuario,
        fecha__date=fecha_dt
    ).order_by('-fecha')

    # Unificar movimientos con tipo
    movimientos = []

    for v in ventas:
        movimientos.append({
            'id': v.id,
            'tipo': 'Venta',
            'tipo_clase': 'success',  # color Bootstrap
            'total': v.total,
            'total_productos': v.total_productos,
            'fecha': v.fecha,
            'objeto': v
        })

    for c in compras:
        movimientos.append({
            'id': c.id,
            'tipo': 'Compra',
            'tipo_clase': 'primary',
            'total': c.total,
            'total_productos': c.total_productos,
            'fecha': c.fecha,
            'objeto': c
        })

    movimientos.sort(key=lambda x: x['fecha'], reverse=True)

    return render(request, 'movimientos/movimientos_dia.html', {
        'usuario': usuario,
        'fecha': fecha_dt,
        'movimientos': movimientos,
        'num_ventas': ventas.count(),
        'num_compras': compras.count(),
        'total_ventas': sum(m['total'] for m in movimientos if m['tipo'] == 'Venta'),
    })