import json
import csv
import re
import time
import requests as http_requests
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.conf import settings

from . import influx, gnuradio, testbed, scenario_engine
from .models import Scenario, ScenarioRun, RunLog

# qwen2.5 иногда самопроизвольно "переключается" на китайский язык (утечка из
# китаецентричного обучающего корпуса), обычно дублируя уже сказанное по-русски.
# Обрезаем ответ на первом иероглифе CJK — до этого места текст обычно уже полезен.
_CJK_RE = re.compile(r'[一-鿿]')


def _strip_cjk_tail(text: str) -> str:
    m = _CJK_RE.search(text)
    if not m:
        return text
    return text[:m.start()].rstrip(' \n:：')


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


@login_required
def scenarios_page(request):
    return render(request, 'dashboard/scenarios.html', {
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
    LOSS_METRICS = {'loss_dl': 'dl', 'loss_ul': 'ul'}

    metric   = request.GET.get('metric', 'dl')
    start    = request.GET.get('start', '-30m')
    end      = request.GET.get('end', 'now()')
    interval = request.GET.get('interval', '30s')

    if metric in LOSS_METRICS:
        data, err = influx.get_loss_history(LOSS_METRICS[metric], start, end, interval)
        if err:
            return JsonResponse({'ok': False, 'error': err}, status=502)
        return JsonResponse({'ok': True, 'series': data, 'unit': '%'})

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

@login_required
@require_GET
def api_gnr_status(request):
    result = gnuradio.status()
    return JsonResponse(result)


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
    n_ue = int(testbed.status().get('n_ues') or 1)
    result = gnuradio.set_noise(noise_type, level, n_ue)
    return JsonResponse(result)


# ── Testbed control ──────────────────────────────────────────────────────────

@login_required
@require_GET
def api_testbed_status(request):
    return JsonResponse(testbed.status())


@admin_required
@require_POST
def api_testbed_start(request):
    body = json.loads(request.body)
    n = int(body.get('n', 1))
    if not (1 <= n <= 7):
        return JsonResponse({'ok': False, 'error': 'n must be 1-7'}, status=400)
    return JsonResponse(testbed.start(n))


@admin_required
@require_POST
def api_testbed_stop(request):
    return JsonResponse(testbed.stop())


# ── Process manager: per-component control ──────────────────────────────────

@login_required
@require_GET
def api_components(request):
    return JsonResponse(testbed.list_components())


@login_required
@require_GET
def api_component_status(request, name):
    return JsonResponse(testbed.component_status(name))


@admin_required
@require_POST
def api_component_start(request, name):
    body = json.loads(request.body or b'{}')
    n = int(body.get('n', 1))
    if not (1 <= n <= 7):
        return JsonResponse({'ok': False, 'error': 'n must be 1-7'}, status=400)
    return JsonResponse(testbed.component_start(name, n))


@admin_required
@require_POST
def api_component_stop(request, name):
    return JsonResponse(testbed.component_stop(name))


@login_required
@require_GET
def api_component_logs_stream(request, name):
    """
    Server-Sent Events log tail for one component. Polls testbed_helper's
    offset-based /logs endpoint (itself a plain synchronous file read) and
    forwards new lines to the browser as SSE 'data:' frames.

    Capped at 10 minutes per connection — EventSource auto-reconnects, so this
    just bounds how long a single dev-server worker thread stays tied up.
    """
    if name not in testbed.COMPONENT_NAMES:
        return JsonResponse({'ok': False, 'error': 'unknown component'}, status=404)

    def event_stream():
        offset = 0
        deadline = time.time() + 600
        yield ': connected\n\n'
        while time.time() < deadline:
            result = testbed.component_logs(name, offset)
            if not result.get('ok'):
                yield f"event: error\ndata: {json.dumps(result)}\n\n"
                time.sleep(2)
                continue
            offset = result.get('offset', offset)
            for line in result.get('lines', []):
                yield f"data: {json.dumps({'line': line})}\n\n"
            time.sleep(1)
        yield ': timeout, reconnect\n\n'

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── Scenario engine ───────────────────────────────────────────────────────────

def _scenario_public(s: Scenario) -> dict:
    return {
        'slug': s.slug,
        'name': s.name,
        'description': s.description,
        'parameters': s.definition.get('parameters', {}),
        'is_builtin': s.is_builtin,
    }


def _run_public(r: ScenarioRun) -> dict:
    return {
        'id': r.pk,
        'scenario': r.scenario.slug,
        'scenario_name': r.scenario.name,
        'params': r.params,
        'status': r.status,
        'current_step': r.current_step,
        'error': r.error,
        'started_at': r.started_at.isoformat() if r.started_at else None,
        'finished_at': r.finished_at.isoformat() if r.finished_at else None,
        'created_at': r.created_at.isoformat(),
    }


@login_required
@require_GET
def api_scenarios(request):
    scenario_engine.sync_scenarios()
    scenarios = [_scenario_public(s) for s in Scenario.objects.all().order_by('name')]
    return JsonResponse({'ok': True, 'scenarios': scenarios})


@login_required
@require_GET
def api_scenario_detail(request, slug):
    try:
        s = Scenario.objects.get(slug=slug)
    except Scenario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)
    return JsonResponse({'ok': True, 'scenario': _scenario_public(s)})


@admin_required
@require_POST
def api_scenario_run(request, slug):
    try:
        s = Scenario.objects.get(slug=slug)
    except Scenario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)
    overrides = json.loads(request.body or b'{}')
    try:
        run = scenario_engine.start_run(s, overrides)
    except scenario_engine.ParamValidationError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True, 'run': _run_public(run)})


@login_required
@require_GET
def api_runs(request):
    qs = ScenarioRun.objects.select_related('scenario').all()
    slug = request.GET.get('scenario')
    if slug:
        qs = qs.filter(scenario__slug=slug)
    limit = min(int(request.GET.get('limit', 50)), 200)
    runs = [_run_public(r) for r in qs[:limit]]
    return JsonResponse({'ok': True, 'runs': runs})


@login_required
@require_GET
def api_run_detail(request, run_id):
    try:
        r = ScenarioRun.objects.select_related('scenario').get(pk=run_id)
    except ScenarioRun.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)
    return JsonResponse({'ok': True, 'run': _run_public(r)})


@admin_required
@require_POST
def api_run_stop(request, run_id):
    try:
        r = ScenarioRun.objects.get(pk=run_id)
    except ScenarioRun.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)
    if r.status != ScenarioRun.STATUS_RUNNING:
        return JsonResponse({'ok': False, 'error': f'run is {r.status}, not running'}, status=409)
    scenario_engine.request_stop(r)
    return JsonResponse({'ok': True})


@login_required
@require_GET
def api_run_logs_stream(request, run_id):
    """
    SSE tail of RunLog for one run. Closes itself once the run reaches a
    terminal status and every log up to that point has been sent, instead of
    relying on the 10-minute cap used for component logs — early-warning runs
    are declared in hours, not minutes.
    """
    try:
        ScenarioRun.objects.get(pk=run_id)
    except ScenarioRun.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)

    def event_stream():
        last_id = 0
        deadline = time.time() + 6 * 3600
        yield ': connected\n\n'
        while time.time() < deadline:
            entries = list(RunLog.objects.filter(run_id=run_id, id__gt=last_id).order_by('id'))
            run_status = ScenarioRun.objects.values_list('status', flat=True).filter(pk=run_id).first()
            for entry in entries:
                last_id = entry.id
                payload = {
                    'id': entry.id,
                    'level': entry.level,
                    'step': entry.step_index,
                    'message': entry.message,
                    'ts': entry.ts.isoformat(),
                }
                yield f"data: {json.dumps(payload)}\n\n"
            if run_status not in (ScenarioRun.STATUS_RUNNING, ScenarioRun.STATUS_IDLE) and not entries:
                yield f"event: done\ndata: {json.dumps({'status': run_status})}\n\n"
                return
            time.sleep(1)
        yield ': timeout, reconnect\n\n'

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── AI insight (Ollama) ───────────────────────────────────────────────────────

@login_required
@require_POST
def api_ai_insight(request):
    """
    POST {} → ask Ollama qwen2.5:7b-instruct to analyse current UE stats.
    Returns {'ok': True, 'text': '...'} or {'ok': False, 'error': '...'}.
    Requires at least one UE row in InfluxDB.
    """
    ues, err = influx.get_current_ue_stats()
    if err:
        return JsonResponse({'ok': False, 'error': f'InfluxDB: {err}'}, status=502)
    if not ues:
        return JsonResponse({'ok': False, 'error': 'Нет данных UE в InfluxDB'}, status=503)

    lines = '\n'.join(
        f"UE{u['id']} (RNTI {u['rnti']}): DL={u['dl']} Mbps, UL={u['ul']} Mbps, "
        f"CQI={u['cqi']}, MCS={u['mcs']}"
        for u in ues
    )
    prompt = (
        'Ты — эксперт по сетям 5G NR. Вот текущие метрики абонентов srsRAN gNB:\n\n'
        f'{lines}\n\n'
        'Оцени качество связи, укажи слабые места и дай одну конкретную рекомендацию '
        '(pathloss, MCS, планировщик). '
        'Отвечай ТОЛЬКО на русском языке, без других языков и иероглифов. '
        'Максимум 3 коротких предложения, без списков и заголовков.'
    )

    try:
        r = http_requests.post(
            f'{settings.OLLAMA_URL}/api/generate',
            json={
                'model': 'qwen2.5:7b-instruct', 'prompt': prompt, 'stream': False,
                'options': {'temperature': 0.3},
            },
            timeout=60,
        )
        r.raise_for_status()
        text = _strip_cjk_tail(r.json().get('response', '').strip())
        return JsonResponse({'ok': True, 'text': text})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=502)


@login_required
def ai_page(request):
    return render(request, 'dashboard/ai.html', {
        'user': request.user,
        'is_admin': request.user.is_admin_role,
    })


@login_required
@require_POST
def api_ai_chat(request):
    """
    Multi-turn AI chat with automatic network context injection.
    POST {message: str, history: [{role, content}]}
    Returns {ok, response}
    """
    body = json.loads(request.body)
    user_message = body.get('message', '').strip()
    history = body.get('history', [])

    if not user_message:
        return JsonResponse({'ok': False, 'error': 'Пустое сообщение'}, status=400)

    ues, err = influx.get_current_ue_stats()
    if ues and not err:
        lines = '\n'.join(
            f"UE{u['id']} (RNTI {u['rnti']}): DL={u['dl']} Mbps, UL={u['ul']} Mbps, "
            f"CQI={u['cqi']}, MCS={u['mcs']}"
            for u in ues
        )
        network_ctx = f"\n\nТекущие метрики сети srsRAN gNB (реальные данные):\n{lines}"
    else:
        network_ctx = "\n\nМетрики сети сейчас недоступны (нет данных в InfluxDB или gNB не запущен)."

    system_prompt = (
        "Ты — эксперт по сетям 5G NR и srsRAN. "
        "Помогаешь оператору анализировать и оптимизировать тестовый стенд: gNB (srsRAN Project), "
        "srsUE, GNU Radio ZMQ канал, Open5GS 5G Core. "
        "Отвечай ТОЛЬКО на русском языке, без других языков и иероглифов. "
        "Отвечай коротко и по делу — 2-4 предложения, без длинных списков и заголовков, "
        "если пользователь явно не попросил подробностей. "
        "Команды bash давай только если это прямо нужно для диагностики."
        + network_ctx
    )

    messages = [{'role': 'system', 'content': system_prompt}] + history + [{'role': 'user', 'content': user_message}]

    try:
        r = http_requests.post(
            f'{settings.OLLAMA_URL}/api/chat',
            json={
                'model': 'qwen2.5:7b-instruct', 'messages': messages, 'stream': False,
                'options': {'temperature': 0.3},
            },
            timeout=120,
        )
        r.raise_for_status()
        response_text = _strip_cjk_tail(r.json().get('message', {}).get('content', '').strip())
        return JsonResponse({'ok': True, 'response': response_text})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=502)


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
    LOSS_METRICS = {'loss_dl': 'dl', 'loss_ul': 'ul'}

    metric   = request.GET.get('metric', 'dl')
    start    = request.GET.get('start', '-30m')
    end      = request.GET.get('end', 'now()')
    interval = request.GET.get('interval', '30s')

    if metric in LOSS_METRICS:
        data, err = influx.get_loss_history(LOSS_METRICS[metric], start, end, interval)
        field_name = metric
    else:
        measurement, field = METRIC_MAP.get(metric, ('ue', 'dl_brate'))
        data, err = influx.get_history(measurement, field, start, end, interval)
        field_name = field

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="srsran_{metric}_{start}.csv"'
    writer = csv.writer(response)
    writer.writerow(['time', 'rnti', field_name])
    if data:
        for rnti, points in data.items():
            for p in points:
                writer.writerow([p['t'], rnti, p['v']])
    return response
