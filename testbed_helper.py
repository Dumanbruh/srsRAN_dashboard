#!/usr/bin/env python3
"""
testbed_helper.py — host-side control service for the srsRAN testbed.

Runs as the plain user (via `screen -dmS testbed_helper python3 testbed_helper.py`,
NEVER via sudo) on 127.0.0.1:8090. The Django dashboard (in Docker, network_mode: host)
calls this over localhost to start/stop/status the testbed, since the container has
no host filesystem or process access.

Stdlib-only by design — avoids repeating the root-vs-user Python module mismatch bug
hit earlier (root's Python lacked the user's ~/.local/websocket-client package).

No auth on this service — it only listens on 127.0.0.1, same trust boundary as the
existing unauthenticated GNU Radio XML-RPC (:8080) and InfluxDB (:8086). Django's
admin_required decorator is the real access-control boundary for start/stop.

Process manager (added for the scenario engine): in addition to the original
whole-testbed /start, /stop, /status, this exposes per-component control:

  GET  /components                    -> status of every known component
  GET  /components/<name>/status      -> status of one component
  POST /components/<name>/start       -> {n: int}  (n only used by gnuradio/ue)
  POST /components/<name>/stop        -> {}
  GET  /components/<name>/logs        -> ?offset=<byte offset>, tails a log file

<name> is one of: gnuradio, gnb, ue, bridge. All state changes are delegated to
start_testbed.sh's component-start/component-stop subcommands (same proven bash
logic as the whole-stack path, not reimplemented here) so there is exactly one
place that knows how to actually launch each component.
"""

import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = '127.0.0.1'
PORT = 8090
START_SCRIPT = '/home/user/srsRAN_dashboard/start_testbed.sh'
ROOT_OPS_SCRIPT = '/home/user/srsRAN_dashboard/testbed_root_ops.sh'
LOG_DIR = '/tmp/testbed_logs'
MAX_N = 7
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

COMPONENT_NAMES = ('gnuradio', 'gnb', 'ue', 'bridge')
# Which components accept an "n" (UE count) parameter on start.
TAKES_N = {'gnuradio', 'ue'}
# Log file per component, where one exists. 'ue' has no single aggregate log
# today (per-netns srsUE processes are managed inside testbed_root_ops.sh,
# which doesn't currently expose one file) — logs() reports that explicitly
# rather than pretending an empty file exists.
LOG_PATHS = {
    'gnuradio': f'{LOG_DIR}/gnuradio.log',
    'bridge':   f'{LOG_DIR}/bridge.log',
    'gnb':      f'{LOG_DIR}/gnb.log',
}

lock = threading.RLock()  # reentrant: do_POST holds it while calling get_status()
state = {'starting': False, 'stopping': False}
# Per-component busy flag while a component-start/component-stop subprocess runs.
component_transition = {}


def run(args, timeout=None):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


# ── Component status (shared by /status and /components) ───────────────────

def _screen_running(name: str) -> bool:
    screens = run(['screen', '-list']).stdout
    return bool(re.search(rf'\.{re.escape(name)}\b', screens))


def _gnb_running() -> bool:
    out = run(['sudo', '-n', ROOT_OPS_SCRIPT, 'gnb_status'])
    return out.returncode == 0 and 'running' in out.stdout


def _ue_list() -> list:
    out = run(['sudo', '-n', ROOT_OPS_SCRIPT, 'ues_status'])
    ues = []
    if out.returncode == 0:
        clean = ANSI_RE.sub('', out.stdout)
        for m in re.finditer(r'UE (\d+): \[В СЕТИ\]\s*-\s*IP: (\S+)', clean):
            ues.append({'id': int(m.group(1)), 'ip': m.group(2), 'up': True})
        for m in re.finditer(r'UE (\d+): \[ЗАПУЩЕН\]', clean):
            ues.append({'id': int(m.group(1)), 'ip': None, 'up': False})
    ues.sort(key=lambda u: u['id'])
    return ues


def component_status(name: str) -> dict:
    busy = component_transition.get(name)
    if name == 'gnuradio':
        up = _screen_running('gnuradio')
        return {'name': name, 'state': 'running' if up else 'stopped', 'busy': busy}
    if name == 'bridge':
        up = _screen_running('metrics_bridge')
        return {'name': name, 'state': 'running' if up else 'stopped', 'busy': busy}
    if name == 'gnb':
        up = _gnb_running()
        return {'name': name, 'state': 'running' if up else 'stopped', 'busy': busy}
    if name == 'ue':
        ues = _ue_list()
        n_up = sum(1 for u in ues if u['up'])
        if not ues:
            ue_state = 'stopped'
        elif n_up == len(ues):
            ue_state = 'running'
        else:
            ue_state = 'degraded'
        return {'name': name, 'state': ue_state, 'ues': ues, 'busy': busy}
    return {'name': name, 'state': 'unknown', 'error': 'no such component'}


def get_status():
    """Whole-testbed status — unchanged response shape (dashboard/testbed.py + UI depend on it)."""
    with lock:
        starting = state['starting']
        stopping = state['stopping']

    gnuradio = _screen_running('gnuradio')
    bridge = _screen_running('metrics_bridge')
    gnb = _gnb_running()
    ue_ips = _ue_list()

    running = gnb and gnuradio and bridge and len(ue_ips) > 0

    return {
        'running': running,
        'starting': starting,
        'stopping': stopping,
        'n_ues': len(ue_ips),
        'ues': ue_ips,
        'gnb': gnb,
        'gnuradio': gnuradio,
        'bridge': bridge,
    }


# ── Whole-testbed start/stop (unchanged) ─────────────────────────────────────

def do_start(n):
    try:
        subprocess.run(['bash', START_SCRIPT, 'start', str(n)], timeout=180)
    finally:
        with lock:
            state['starting'] = False


def do_stop():
    try:
        run(['bash', START_SCRIPT, 'stop'], timeout=60)
    finally:
        with lock:
            state['stopping'] = False


# ── Per-component start/stop/logs (process manager) ─────────────────────────

def component_start(name: str, n: int) -> dict:
    if name not in COMPONENT_NAMES:
        return {'ok': False, 'error': f'unknown component: {name}'}
    with lock:
        busy = component_transition.get(name)
        if busy:
            return {'ok': False, 'error': f'{name} is already {busy}'}
        component_transition[name] = 'starting'

    def _run():
        try:
            args = ['bash', START_SCRIPT, 'component-start', name]
            if name in TAKES_N:
                args.append(str(n))
            subprocess.run(args, timeout=90)
        finally:
            with lock:
                component_transition.pop(name, None)

    threading.Thread(target=_run, daemon=True).start()
    return {'ok': True, 'starting': True}


def component_stop(name: str) -> dict:
    if name not in COMPONENT_NAMES:
        return {'ok': False, 'error': f'unknown component: {name}'}
    with lock:
        busy = component_transition.get(name)
        if busy:
            return {'ok': False, 'error': f'{name} is already {busy}'}
        component_transition[name] = 'stopping'

    def _run():
        try:
            subprocess.run(['bash', START_SCRIPT, 'component-stop', name], timeout=60)
        finally:
            with lock:
                component_transition.pop(name, None)

    threading.Thread(target=_run, daemon=True).start()
    return {'ok': True, 'stopping': True}


def component_load(ue_ids: list, bitrate_mbps: float, duration_s: int, direction: str) -> dict:
    """
    One-shot iperf3 load burst, run as the CLIENT inside each UE's own netns
    (via testbed_root_ops.sh's iperf_client — root-only, narrowly scoped).
    The server sits on the host with no privilege needed at all (plain
    `iperf3 -s`, the same thing that was already proven to work by hand).
    Direction is just iperf3's own -R flag: 'ul' = UE sends (default),
    'dl' = UE receives (-R). Neither direction needs a server inside the UE
    netns — that mismatch (server tried on the wrong side) is what didn't
    work before.
    """
    ues = {u['id']: u for u in _ue_list() if u.get('up')}
    missing = [i for i in ue_ids if i not in ues]
    if missing:
        return {'ok': False, 'error': f'UE(s) not up: {missing}'}

    results = {}
    results_lock = threading.Lock()

    def _run_one(ue_id):
        try:
            out = subprocess.run(
                ['bash', START_SCRIPT, 'ue-load', str(ue_id), str(duration_s), str(bitrate_mbps), direction],
                capture_output=True, text=True, timeout=duration_s + 20,
            )
            try:
                data = json.loads(out.stdout)
            except (json.JSONDecodeError, ValueError):
                data = None
            if out.returncode != 0 or data is None or data.get('error'):
                err = (data.get('error') if data else None) or (out.stderr or out.stdout)[-300:]
                summary = {'ok': False, 'error': err}
            else:
                field = 'sum_received' if direction == 'dl' else 'sum_sent'
                bps = data.get('end', {}).get(field, {}).get('bits_per_second', 0)
                summary = {'ok': True, 'mbps': round(bps / 1e6, 2)}
        except Exception as e:
            summary = {'ok': False, 'error': str(e)}
        with results_lock:
            results[ue_id] = summary

    threads = [threading.Thread(target=_run_one, args=(i,)) for i in ue_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=duration_s + 25)

    return {'ok': True, 'results': results}


def component_logs(name: str, offset: int) -> dict:
    if name not in COMPONENT_NAMES:
        return {'ok': False, 'error': f'unknown component: {name}'}
    path = LOG_PATHS.get(name)
    if path is None:
        return {'ok': False, 'error': f'no log file for component: {name}'}
    if not os.path.exists(path):
        return {'ok': True, 'lines': [], 'offset': 0, 'size': 0}

    size = os.path.getsize(path)
    if offset < 0 or offset > size:
        offset = 0  # log rotated/truncated since last poll — restart from the top

    with open(path, 'r', errors='replace') as f:
        f.seek(offset)
        chunk = f.read()
        new_offset = f.tell()

    lines = chunk.splitlines() if chunk else []
    return {'ok': True, 'lines': lines, 'offset': new_offset, 'size': size}


# ── HTTP ──────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split('/') if p]
        qs = parse_qs(parsed.query)

        if parsed.path == '/status':
            self._json(get_status())
        elif parts == ['components']:
            self._json({'ok': True, 'components': {n: component_status(n) for n in COMPONENT_NAMES}})
        elif len(parts) == 3 and parts[0] == 'components' and parts[2] == 'status':
            self._json({'ok': True, **component_status(parts[1])})
        elif len(parts) == 3 and parts[0] == 'components' and parts[2] == 'logs':
            try:
                offset = int(qs.get('offset', ['0'])[0])
            except ValueError:
                offset = 0
            self._json(component_logs(parts[1], offset))
        else:
            self._json({'ok': False, 'error': 'not found'}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split('/') if p]
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length) if length else b'{}'
        try:
            body = json.loads(raw or b'{}')
        except json.JSONDecodeError:
            body = {}

        if parsed.path == '/start':
            n = body.get('n', 1)
            if not isinstance(n, int) or not (1 <= n <= MAX_N):
                self._json({'ok': False, 'error': f'n must be 1-{MAX_N}'}, 400)
                return
            with lock:
                if state['starting'] or state['stopping']:
                    self._json({'ok': False, 'error': 'testbed is already starting/stopping'}, 409)
                    return
                st = get_status()
                if st['running']:
                    self._json({'ok': False, 'error': 'testbed already running'}, 409)
                    return
                state['starting'] = True
            threading.Thread(target=do_start, args=(n,), daemon=True).start()
            self._json({'ok': True, 'starting': True})

        elif parsed.path == '/stop':
            with lock:
                if state['starting'] or state['stopping']:
                    self._json({'ok': False, 'error': 'testbed is already starting/stopping'}, 409)
                    return
                state['stopping'] = True
            threading.Thread(target=do_stop, daemon=True).start()
            self._json({'ok': True})

        elif len(parts) == 3 and parts[0] == 'components' and parts[2] == 'start':
            name = parts[1]
            n = body.get('n', 1)
            if not isinstance(n, int) or not (1 <= n <= MAX_N):
                n = 1
            self._json(component_start(name, n))

        elif len(parts) == 3 and parts[0] == 'components' and parts[2] == 'stop':
            name = parts[1]
            self._json(component_stop(name))

        elif parsed.path in ('/load/dl', '/load/ul'):
            direction = 'dl' if parsed.path == '/load/dl' else 'ul'
            ue_ids = body.get('ue_ids', [])
            bitrate_mbps = body.get('bitrate_mbps', 1)
            duration_s = body.get('duration_s', 10)
            if not isinstance(ue_ids, list) or not ue_ids:
                self._json({'ok': False, 'error': 'ue_ids must be a non-empty list'}, 400)
                return
            self._json(component_load(ue_ids, float(bitrate_mbps), int(duration_s), direction))

        else:
            self._json({'ok': False, 'error': 'not found'}, 404)

    def log_message(self, fmt, *args):
        pass  # keep stdout quiet; screen log file captures errors via server default


if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'testbed_helper listening on {HOST}:{PORT}')
    server.serve_forever()
