import json
import csv
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponse

from . import influx, gnuradio


def admin_required(view_func):
    """Only admin-role users can call this view."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin_role:
            return JsonResponse({'error': 'Нет доступа. Требуется роль admin.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def index(request):
    return render(request, 'dashboard/dashboard.html', {
        'user': request.user,
        'is_admin': request.user.is_admin_role,
    })


# ── Debug ──────────────────────────────────────────────────────────────────────

@require_GET
def api_debug(request):
    return JsonResponse({
        'measurements': influx.query('SHOW MEASUREMENTS'),
        'fields':       influx.query('SHOW FIELD KEYS'),
        'tags':         influx.query('SHOW TAG KEYS'),
        'sample':       influx.query('SELECT * FROM /.*/ LIMIT 3'),
    }, json_dumps_params={'indent': 2})


# ── API: read ──────────────────────────────────────────────────────────────────

@login_required
@require_GET
def api_stats(request):
    """Current UE stats (polled every second)."""
    ues, err = influx.get_current_ue_stats()
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=502)
    return JsonResponse({'ok': True, 'ues': ues})


@login_required
@require_GET
def api_history(request):
    METRIC_MAP = {
        'dl':      ('ue', 'dl_brate',   True),
        'ul':      ('ue', 'ul_brate',   True),
        'mcs':     ('ue', 'dl_mcs',     False),
        'ul_mcs':  ('ue', 'ul_mcs',     False),
        'bler_dl': ('ue', 'dl_nof_nok', False),
        'bler_ul': ('ue', 'ul_nof_nok', False),
    }

    metric   = request.GET.get('metric', 'dl')
    start    = request.GET.get('start', '-30m')
    end      = request.GET.get('end', 'now()')
    interval = request.GET.get('interval', '30s')

    if metric not in METRIC_MAP:
        return JsonResponse({'ok': False, 'error': 'unknown metric'}, status=400)

    measurement, field, scale_mbps = METRIC_MAP[metric]
    data, err = influx.get_history(measurement, field, start, end, interval)
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=502)

    if scale_mbps and data:
        for rnti in data:
            for pt in data[rnti]:
                if pt['v'] is not None:
                    pt['v'] = round(pt['v'] / 1e6, 3)

    return JsonResponse({'ok': True, 'series': data, 'unit': 'Mbps' if scale_mbps else ''})


# ── API: control (admin only) ──────────────────────────────────────────────────

@admin_required
@require_POST
def api_pathloss(request, ue_id):
    body = json.loads(request.body)
    value = float(body.get('value', 0))
    result = gnuradio.set_pathloss(ue_id, value)
    return JsonResponse(result)


@admin_required
@require_POST
def api_toggle_ue(request, ue_id):
    body = json.loads(request.body)
    active = bool(body.get('active', True))
    result = gnuradio.set_pathloss(ue_id, body.get('pathloss', 0) if active else 100)
    return JsonResponse(result)


@admin_required
@require_POST
def api_noise(request):
    body = json.loads(request.body)
    noise_type = body.get('type', 'none')
    level = float(body.get('level', 0))
    result = gnuradio.set_noise(noise_type, level)
    return JsonResponse(result)


# ── Export ─────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def api_export_csv(request):
    METRIC_MAP = {
        'dl':      ('ue', 'dl_brate'),
        'ul':      ('ue', 'ul_brate'),
        'mcs':     ('ue', 'dl_mcs'),
        'ul_mcs':  ('ue', 'ul_mcs'),
        'bler_dl': ('ue', 'dl_nof_nok'),
        'bler_ul': ('ue', 'ul_nof_nok'),
    }
    metric   = request.GET.get('metric', 'dl')
    start    = request.GET.get('start', '-30m')
    end      = request.GET.get('end', 'now()')
    interval = request.GET.get('interval', '30s')

    measurement, field = METRIC_MAP.get(metric, ('ue', 'dl_brate'))
    data, err = influx.get_history(measurement, field, start, end, interval)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="srsran_{metric}_{start}.csv"'
    writer = csv.writer(response)
    writer.writerow(['time', 'rnti', field])
    if data:
        for rnti, points in data.items():
            for p in points:
                writer.writerow([p['t'], rnti, p['v']])
    return response
