import requests
from django.conf import settings

COMPONENT_NAMES = ('gnuradio', 'gnb', 'ue', 'bridge')


def _url(path: str) -> str:
    return f'{settings.TESTBED_HELPER_URL}{path}'


def status() -> dict:
    try:
        r = requests.get(_url('/status'), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def start(n: int) -> dict:
    try:
        r = requests.post(_url('/start'), json={'n': n}, timeout=5)
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def stop() -> dict:
    try:
        r = requests.post(_url('/stop'), json={}, timeout=15)
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── Process manager: per-component control ──────────────────────────────────

def list_components() -> dict:
    try:
        r = requests.get(_url('/components'), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def component_status(name: str) -> dict:
    try:
        r = requests.get(_url(f'/components/{name}/status'), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def component_start(name: str, n: int = 1) -> dict:
    try:
        r = requests.post(_url(f'/components/{name}/start'), json={'n': n}, timeout=5)
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def component_stop(name: str) -> dict:
    try:
        r = requests.post(_url(f'/components/{name}/stop'), json={}, timeout=5)
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def component_logs(name: str, offset: int = 0) -> dict:
    try:
        r = requests.get(
            _url(f'/components/{name}/logs'),
            params={'offset': offset},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def load_dl(ue_ids: list, bitrate_mbps: float, duration_s: int) -> dict:
    """Blocking call — waits out the full iperf3 burst (duration_s) plus buffer."""
    try:
        r = requests.post(
            _url('/load/dl'),
            json={'ue_ids': ue_ids, 'bitrate_mbps': bitrate_mbps, 'duration_s': duration_s},
            timeout=duration_s + 25,
        )
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def load_ul(ue_ids: list, bitrate_mbps: float, duration_s: int) -> dict:
    """Blocking call, same shape as load_dl but UE-sends-to-host direction."""
    try:
        r = requests.post(
            _url('/load/ul'),
            json={'ue_ids': ue_ids, 'bitrate_mbps': bitrate_mbps, 'duration_s': duration_s},
            timeout=duration_s + 25,
        )
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}
