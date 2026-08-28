"""
scenario_engine.py — declarative scenario executor.

Loads step sequences from dashboard/scenarios/*.yml (see those files for the
step vocabulary), resolves {{parameter}} templates against a run's params,
and executes them one at a time in a background thread, writing progress to
RunLog and status to ScenarioRun. Steps that touch real processes go through
dashboard/testbed.py (which itself talks to testbed_helper.py on the host —
see that module's docstring for why); steps that are simple RPCs go straight
through dashboard/gnuradio.py.
"""

import logging
import re
import threading
import time
from pathlib import Path

import yaml
from django.utils import timezone

from . import gnuradio as gnuradio_client
from . import testbed as testbed_client
from .models import RunLog, Scenario, ScenarioRun

logger = logging.getLogger(__name__)

SCENARIOS_DIR = Path(__file__).resolve().parent / 'scenarios'

PARAM_CASTERS = {
    'int': int,
    'float': float,
    'bool': lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ('1', 'true', 'yes', 'on'),
    'str': str,
    'choice': str,
}


class StepFailed(Exception):
    pass


class StopRequested(Exception):
    pass


class ParamValidationError(Exception):
    pass


# ── Loading scenarios from YAML ──────────────────────────────────────────────

def sync_scenarios():
    """Upsert every dashboard/scenarios/*.yml into the Scenario table by slug.
    Called at the top of the catalog view — new scenarios appear just by
    dropping a file, no code/deploy step needed."""
    if not SCENARIOS_DIR.exists():
        return
    for path in sorted(SCENARIOS_DIR.glob('*.yml')):
        with open(path, encoding='utf-8') as f:
            definition = yaml.safe_load(f)
        slug = definition.get('slug') or path.stem
        Scenario.objects.update_or_create(
            slug=slug,
            defaults={
                'name': definition.get('name', slug),
                'description': definition.get('description', ''),
                'definition': definition,
                'is_builtin': True,
            },
        )


def build_run_params(scenario: Scenario, overrides: dict) -> dict:
    """Merge user-supplied overrides onto scenario parameter defaults, cast to
    declared types, clamp to declared min/max. Raises ParamValidationError
    (not a bare cast exception) on bad user input, so the view can turn it
    into a clean 400 instead of a 500."""
    schema = scenario.definition.get('parameters', {}) or {}
    params = {}
    for key, spec in schema.items():
        ptype = spec.get('type', 'str')
        caster = PARAM_CASTERS.get(ptype, str)
        raw = overrides.get(key)
        if raw in (None, ''):
            raw = spec.get('default')
        try:
            value = caster(raw) if raw is not None else None
        except (TypeError, ValueError):
            raise ParamValidationError(f'параметр "{key}": неверное значение {raw!r} (ожидается {ptype})')
        if value is not None and ptype in ('int', 'float'):
            lo, hi = spec.get('min'), spec.get('max')
            if lo is not None:
                value = max(value, caster(lo))
            if hi is not None:
                value = min(value, caster(hi))
        params[key] = value
    return params


# ── Value / condition resolution ─────────────────────────────────────────────

_FULL_TMPL = re.compile(r'^\{\{\s*(\w+)\s*\}\}$')
_INLINE_TMPL = re.compile(r'\{\{\s*(\w+)\s*\}\}')


def resolve(value, params):
    """Recursively substitute {{param}} references. A value that IS exactly
    "{{x}}" resolves to params['x'] with its native type; {{x}} embedded in a
    larger string is stringified in place."""
    if isinstance(value, str):
        m = _FULL_TMPL.match(value.strip())
        if m:
            return params.get(m.group(1))
        return _INLINE_TMPL.sub(lambda mo: str(params.get(mo.group(1), mo.group(0))), value)
    if isinstance(value, dict):
        return {k: resolve(v, params) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, params) for v in value]
    return value


def is_truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


# ── Run context ───────────────────────────────────────────────────────────────

class RunContext:
    def __init__(self, run: ScenarioRun, params: dict):
        self.run = run
        self.params = params

    def log(self, message, level='info', step_index=None):
        RunLog.objects.create(run=self.run, level=level, step_index=step_index, message=message)

    def should_stop(self) -> bool:
        self.run.refresh_from_db(fields=['stop_requested'])
        return self.run.stop_requested

    def checked_sleep(self, total_s: float, poll_s: float = 2.0):
        """Sleep in small increments so a stop request lands within poll_s, not
        after the full duration."""
        end = time.time() + total_s
        while time.time() < end:
            if self.should_stop():
                raise StopRequested()
            time.sleep(min(poll_s, max(end - time.time(), 0)))


# ── Step handlers ─────────────────────────────────────────────────────────────

def h_component_start(ctx, step, idx):
    component = step['component']
    params = resolve(step.get('params', {}), ctx.params)
    n = int(params['n']) if 'n' in params and params['n'] is not None else 1
    result = testbed_client.component_start(component, n)
    if not result.get('ok'):
        raise StepFailed(f'не удалось запустить {component}: {result.get("error")}')
    ctx.log(f'{component}: старт запрошен (n={n})', step_index=idx)


def h_component_stop(ctx, step, idx):
    component = step['component']
    result = testbed_client.component_stop(component)
    if not result.get('ok'):
        ctx.log(f'{component}: остановка вернула ошибку: {result.get("error")}', level='warn', step_index=idx)
    else:
        ctx.log(f'{component}: остановка запрошена', step_index=idx)


def h_wait_ready(ctx, step, idx):
    component = step['component']
    timeout_s = float(resolve(step.get('timeout_s', 30), ctx.params))
    required_n_raw = step.get('n')
    required_n = int(resolve(required_n_raw, ctx.params)) if required_n_raw is not None else None

    # More UEs registering in parallel takes longer than one — a flat timeout
    # tuned for n_ue=1 starts failing real runs around n_ue=3 (seen on real
    # hardware: 60s was enough for 1 UE, not enough for 3). timeout_s_per_ue
    # is optional and additive, so steps that don't set it (gnb/gnuradio/
    # bridge waits, or older scenario files) keep their exact old behaviour.
    per_ue_raw = step.get('timeout_s_per_ue')
    if per_ue_raw is not None and required_n is not None:
        timeout_s += float(resolve(per_ue_raw, ctx.params)) * required_n

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if ctx.should_stop():
            raise StopRequested()
        st = testbed_client.component_status(component)
        # testbed_helper.py's component_status() reports state='running' purely
        # from process/screen-session existence — it has no idea whether THIS
        # scenario's own component-start call actually produced that process.
        # component-start runs the real start_testbed.sh routine in a background
        # thread and marks the component busy='starting' for its whole duration
        # (which, for gnuradio, can itself stop+restart a stale gNB left over
        # from a leftover/failed prior run). If we trust state=='running' while
        # busy is still set, we're seeing a STALE leftover process from before
        # this run — not the fresh one — and race ahead to start UE against a
        # gNB/broker that's mid-restart or about to be torn down underneath us.
        # Seen live: gnuradio/gnb both reported "готово" within ~30ms of the
        # start request (impossible for a real cold start, which sleeps for
        # seconds) while a genuine restart was still running in the background
        # — UE then never attached within timeout. Only trust state once busy
        # has cleared, i.e. the whole start_testbed.sh call actually finished.
        if not st.get('busy'):
            if component == 'ue' and required_n is not None:
                n_up = sum(1 for u in st.get('ues', []) if u.get('up'))
                if n_up >= required_n:
                    ctx.log(f'ue: готово ({n_up}/{required_n})', step_index=idx)
                    return
            elif st.get('state') == 'running':
                ctx.log(f'{component}: готово', step_index=idx)
                return
        time.sleep(2)
    raise StepFailed(f'{component} не стал готов за {timeout_s}с')


def h_set_pathloss(ctx, step, idx):
    ue_id = int(resolve(step['ue_id'], ctx.params))
    value = float(resolve(step['value'], ctx.params))
    result = gnuradio_client.set_pathloss(ue_id, value)
    if not result.get('ok'):
        raise StepFailed(f'set_pathloss UE{ue_id}: {result.get("error")}')
    ctx.log(f'UE{ue_id}: pathloss = {value} дБ', step_index=idx)


def h_ramp_pathloss(ctx, step, idx):
    ue_id = int(resolve(step['ue_id'], ctx.params))
    start = float(resolve(step['from'], ctx.params))
    end = float(resolve(step['to'], ctx.params))
    duration_s = float(resolve(step.get('duration_s', 10), ctx.params))
    steps_n = max(int(resolve(step.get('steps', 20), ctx.params)), 1)
    delay = duration_s / steps_n
    for s in range(steps_n + 1):
        if ctx.should_stop():
            raise StopRequested()
        value = start + (end - start) * (s / steps_n)
        gnuradio_client.set_pathloss(ue_id, value)
        time.sleep(delay)
    ctx.log(f'UE{ue_id}: pathloss {start:g}→{end:g} дБ за {duration_s:g}с', step_index=idx)


def h_apply_pathloss_profile(ctx, step, idx):
    profile = resolve(step['profile'], ctx.params)
    for entry in profile:
        gnuradio_client.set_pathloss(int(entry['ue_id']), float(entry['value']))
    ctx.log(f'применён профиль pathloss: {profile}', step_index=idx)


def h_sleep(ctx, step, idx):
    duration_s = float(resolve(step.get('duration_s', 1), ctx.params))
    if duration_s > 0:
        ctx.checked_sleep(duration_s)
    ctx.log(f'пауза {duration_s:g}с', step_index=idx)


def h_snapshot_metrics(ctx, step, idx):
    label = resolve(step.get('label', ''), ctx.params)
    suffix = f': {label}' if label else ''
    ctx.log(f'снимок метрик{suffix} @ {timezone.now().isoformat()}', step_index=idx)


def _do_load(ctx, step, idx, direction):
    """
    Shared body for h_load_dl / h_load_ul — same step vocabulary, same
    background/blocking semantics, only the direction (and which
    testbed_client function / log labels to use) differs.
    """
    client_fn = testbed_client.load_dl if direction == 'dl' else testbed_client.load_ul
    label = 'DL' if direction == 'dl' else 'UL'
    step_type = f'load_{direction}'

    ue_ids = step.get('ue_ids')
    if ue_ids is not None:
        ue_ids = resolve(ue_ids, ctx.params)
    else:
        n = int(resolve(step.get('n', ctx.params.get('n_ue', 1)), ctx.params))
        ue_ids = list(range(1, n + 1))
    bitrate_mbps = float(resolve(step.get('bitrate_mbps', 10), ctx.params))
    duration_s = int(resolve(step.get('duration_s', 30), ctx.params))
    background = is_truthy(resolve(step.get('background', False), ctx.params))

    if bitrate_mbps <= 0:
        ctx.log(f'{step_type}: нагрузка 0 Мбит/с — просто жду {duration_s}с', step_index=idx)
        ctx.checked_sleep(duration_s)
        return

    if background:
        # Fire-and-forget: subsequent steps (e.g. a pathloss ramp) run while
        # this keeps generating traffic on its own thread. testbed_helper's
        # /load/dl|ul call is self-bounding (subprocess timeout=duration_s+20),
        # so it can't outlive teardown by more than ~20s even if abandoned.
        def _bg():
            result = client_fn(ue_ids, bitrate_mbps, duration_s)
            if result.get('ok'):
                ctx.log(f'(фон) {label}-нагрузка завершена: {result.get("results")}', step_index=idx)
            else:
                ctx.log(f'(фон) {step_type} ошибка: {result.get("error")}', level='warn', step_index=idx)
        threading.Thread(target=_bg, daemon=True).start()
        ctx.log(
            f'{label}-нагрузка запущена в фоне: {bitrate_mbps:g} Мбит/с × {len(ue_ids)} UE, до {duration_s}с',
            step_index=idx,
        )
        return

    result = client_fn(ue_ids, bitrate_mbps, duration_s)
    if not result.get('ok'):
        raise StepFailed(f'{step_type}: {result.get("error")}')
    # testbed_helper's /load/dl|ul returns ok=True at the top level whenever
    # the orchestration itself ran without throwing — that's independent of
    # whether any UE's iperf3 actually connected. Without checking per-UE
    # results too, a load step where every single UE failed still logged as
    # if it succeeded and let the run finish "completed", silently hiding
    # that zero traffic was ever generated.
    per_ue = result.get('results') or {}
    succeeded = [uid for uid, r in per_ue.items() if r.get('ok')]
    if per_ue and not succeeded:
        raise StepFailed(f'{step_type}: ни один UE не принял нагрузку: {per_ue}')
    ctx.log(
        f'{label}-нагрузка {bitrate_mbps:g} Мбит/с × {len(ue_ids)} UE, {duration_s}с: {result.get("results")}',
        step_index=idx,
    )


def h_load_dl(ctx, step, idx):
    _do_load(ctx, step, idx, 'dl')


def h_load_ul(ctx, step, idx):
    _do_load(ctx, step, idx, 'ul')


def h_apply_slice_profile(ctx, step, idx):
    profile = resolve(step['profile'], ctx.params)
    ctx.log(
        '[ЗАГЛУШКА] реального управления PRB-слайсингом на этом стенде нет '
        f'(нет FlexRIC-xApp для slicing) — профиль только записан в лог: {profile}',
        level='warn', step_index=idx,
    )


def h_repeat(ctx, step, idx):
    count = int(resolve(step.get('count', 1), ctx.params))
    inner = step.get('steps', [])
    for c in range(count):
        if ctx.should_stop():
            raise StopRequested()
        ctx.log(f'repeat {c + 1}/{count}', step_index=idx)
        _run_steps(ctx, inner, index_base=idx)


STEP_HANDLERS = {
    'component_start': h_component_start,
    'component_stop': h_component_stop,
    'wait_ready': h_wait_ready,
    'set_pathloss': h_set_pathloss,
    'ramp_pathloss': h_ramp_pathloss,
    'apply_pathloss_profile': h_apply_pathloss_profile,
    'load_dl': h_load_dl,
    'load_ul': h_load_ul,
    'sleep': h_sleep,
    'snapshot_metrics': h_snapshot_metrics,
    'apply_slice_profile': h_apply_slice_profile,
    'repeat': h_repeat,
}


# ── Step-list walking ─────────────────────────────────────────────────────────

def _run_steps(ctx, steps, index_base=0):
    for i, step in enumerate(steps):
        if ctx.should_stop():
            raise StopRequested()
        idx = index_base + i
        ctx.run.current_step = idx
        ctx.run.save(update_fields=['current_step'])

        enabled_if = step.get('enabled_if')
        if enabled_if is not None and not is_truthy(resolve(enabled_if, ctx.params)):
            ctx.log(f'шаг пропущен (условие не выполнено): {step.get("type")}', step_index=idx)
            continue

        step_type = step.get('type')
        handler = STEP_HANDLERS.get(step_type)
        if handler is None:
            raise StepFailed(f'неизвестный тип шага: {step_type}')
        handler(ctx, step, idx)


def _collect_component_stops(steps):
    """Flatten out every component_stop step (including inside repeat blocks),
    in original order — used as a best-effort cleanup pass after cancellation."""
    out = []
    for step in steps:
        if step.get('type') == 'component_stop':
            out.append(step)
        elif step.get('type') == 'repeat':
            out.extend(_collect_component_stops(step.get('steps', [])))
    return out


ALL_COMPONENTS = ('gnuradio', 'gnb', 'ue', 'bridge')
STOP_ORDER = ('bridge', 'ue', 'gnb', 'gnuradio')  # mirrors every scenario YAML's own teardown order


def _wait_components_idle(ctx, timeout_s=100):
    """Block until no component reports a start/stop transition still in
    flight (testbed_helper.py's per-component 'busy' flag). Without this, a
    fresh scenario's own component_start can land while a PREVIOUS run's
    (or a stray dashboard click's) component-start/stop subprocess is still
    running in the background, and gets rejected outright with
    "<component> is already starting" — seen live on a real run."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if ctx.should_stop():
            raise StopRequested()
        if not any(testbed_client.component_status(c).get('busy') for c in ALL_COMPONENTS):
            return
        time.sleep(2)
    ctx.log('пред-запуск: истёк таймаут ожидания освобождения компонентов, продолжаю всё равно', level='warn')


def _pre_run_reset(ctx):
    """Force every scenario to start from a known-clean testbed state,
    regardless of what a previous run left behind. Before this, a run that
    failed (anything other than an explicit stop) never tore down what it
    had already started, so its gnuradio/gnb/ue/bridge just kept running
    until someone noticed — and the next scenario's own component_start
    would either collide with a still-busy transition or silently reuse
    stale, wrongly-configured processes."""
    _wait_components_idle(ctx)
    statuses = {c: testbed_client.component_status(c) for c in ALL_COMPONENTS}
    if all(s.get('state') == 'stopped' for s in statuses.values()):
        return
    ctx.log('пред-запуск: останавливаю компоненты, оставшиеся от предыдущего прогона ...')
    for c in STOP_ORDER:
        testbed_client.component_stop(c)
    _wait_components_idle(ctx)


def _run_cleanup(ctx, steps):
    stops = _collect_component_stops(steps)
    if not stops:
        return
    ctx.log('Останавливаю компоненты (cleanup после остановки прогона) ...')
    for step in stops:
        try:
            h_component_stop(ctx, step, None)
        except Exception as e:
            ctx.log(f'cleanup: ошибка остановки {step.get("component")}: {e}', level='warn')


# ── Public entry points ───────────────────────────────────────────────────────

def start_run(scenario: Scenario, overrides: dict) -> ScenarioRun:
    params = build_run_params(scenario, overrides)
    run = ScenarioRun.objects.create(scenario=scenario, params=params, status=ScenarioRun.STATUS_IDLE)
    threading.Thread(target=execute_run, args=(run.pk,), daemon=True).start()
    return run


def request_stop(run: ScenarioRun):
    run.stop_requested = True
    run.save(update_fields=['stop_requested'])


def execute_run(run_id: int):
    """Runs in a background thread — started right after ScenarioRun is created."""
    run = ScenarioRun.objects.select_related('scenario').get(pk=run_id)
    ctx = RunContext(run, run.params)
    steps = run.scenario.definition.get('steps', [])

    run.status = ScenarioRun.STATUS_RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=['status', 'started_at'])
    ctx.log(f'Запуск сценария "{run.scenario.name}" (params={run.params})')

    try:
        _pre_run_reset(ctx)
        _run_steps(ctx, steps)
        run.status = ScenarioRun.STATUS_COMPLETED
        ctx.log('Прогон завершён успешно.')
    except StopRequested:
        _run_cleanup(ctx, steps)
        run.status = ScenarioRun.STATUS_STOPPED
        ctx.log('Прогон остановлен пользователем.')
    except Exception as e:
        run.status = ScenarioRun.STATUS_FAILED
        run.error = str(e)
        ctx.log(f'ОШИБКА: {e}', level='error')
        logger.exception('scenario run %s failed', run_id)
        _run_cleanup(ctx, steps)
    finally:
        run.finished_at = timezone.now()
        run.save(update_fields=['status', 'error', 'finished_at', 'current_step'])
