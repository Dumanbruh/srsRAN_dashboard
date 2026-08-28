import requests
from django.conf import settings


def _auth_headers() -> dict:
    return {'Authorization': f'Token {settings.INFLUX_TOKEN}'}


def query(q: str) -> dict:
    """Execute InfluxQL query, return raw json."""
    try:
        r = requests.get(
            f'{settings.INFLUX_URL}/query',
            params={'db': settings.INFLUX_DB, 'q': q},
            headers=_auth_headers(),
            timeout=3,
        )
        r.raise_for_status()
        return {'ok': True, 'data': r.json()}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


MAX_UES = 7


def get_current_ue_stats():
    """Latest stats per UE (RNTI), up to MAX_UES."""
    q = (
        'SELECT last("dl_brate"), last("ul_brate"), last("cqi"), last("dl_mcs"), '
        'last("ul_mcs"), last("dl_nof_nok"), last("ul_nof_nok"), '
        'last("dl_nof_ok"), last("ul_nof_ok"), last("snr") '
        'FROM "ue" GROUP BY "rnti"'
    )
    result = query(q)
    if not result['ok']:
        return None, result['error']
    series = result['data'].get('results', [{}])[0].get('series', [])
    ues = []
    for i, s in enumerate(series[:MAX_UES]):
        vals = s.get('values', [[None]*11])[0]
        ues.append({
            'id': i + 1,
            'rnti': s.get('tags', {}).get('rnti', f'UE{i+1}'),
            'dl': round((vals[1] or 0) / 1e6, 2),
            'ul': round((vals[2] or 0) / 1e6, 2),
            'cqi': vals[3] or 0,
            'mcs': vals[4] or 0,
            'ul_mcs': vals[5] or 0,
            'dl_nok': vals[6] or 0,
            'ul_nok': vals[7] or 0,
            'dl_ok': vals[8] or 0,
            'ul_ok': vals[9] or 0,
            'pusch_snr': vals[10] or 0,
        })
    return ues, None


def get_loss_history(direction: str, start: str, end: str, interval: str = '10s'):
    """
    Packet-loss-proxy history (%), per rnti: nof_nok / (nof_ok + nof_nok) * 100.
    There's no direct "packet loss" field in the schema — this is derived from
    the transport-block ok/not-ok counters metrics_bridge.py already writes,
    which is the closest honest proxy available (no ping-based RTT/loss probe
    is wired into this testbed).
    direction: 'dl' or 'ul'
    """
    ok_field = f'{direction}_nof_ok'
    nok_field = f'{direction}_nof_nok'
    if start.startswith('-'):
        where = f"time >= now() - {start.lstrip('-')}"
    else:
        where = f"time >= '{start}' AND time <= '{end}'"
    q = (
        f'SELECT mean("{ok_field}") AS ok, mean("{nok_field}") AS nok FROM "ue" '
        f'WHERE {where} GROUP BY time({interval}), "rnti" fill(null)'
    )
    result = query(q)
    if not result['ok']:
        return None, result['error']
    series = result['data'].get('results', [{}])[0].get('series', [])
    out = {}
    for s in series:
        rnti = s.get('tags', {}).get('rnti', 'unknown')
        cols = s.get('columns', [])
        time_idx = cols.index('time') if 'time' in cols else 0
        ok_idx = cols.index('ok') if 'ok' in cols else 1
        nok_idx = cols.index('nok') if 'nok' in cols else 2
        points = []
        for row in s.get('values', []):
            ok, nok = row[ok_idx], row[nok_idx]
            if ok is None and nok is None:
                continue
            total = (ok or 0) + (nok or 0)
            loss_pct = round((nok or 0) / total * 100, 2) if total > 0 else 0.0
            points.append({'t': row[time_idx], 'v': loss_pct})
        out[rnti] = points
    return out, None


def get_history(measurement: str, field: str, start: str, end: str, interval: str = '10s'):
    """
    Time-series data for charts.
    start/end: InfluxDB time strings like '-1h', '-30m', '2024-01-01T00:00:00Z'
    interval: group by time bucket
    """
    if start.startswith('-'):
        where = f"time >= now() - {start.lstrip('-')}"
    else:
        where = f"time >= '{start}' AND time <= '{end}'"
    q = (
        f'SELECT mean("{field}") FROM "{measurement}" '
        f'WHERE {where} GROUP BY time({interval}), "rnti" fill(null)'
    )
    result = query(q)
    if not result['ok']:
        return None, result['error']
    series = result['data'].get('results', [{}])[0].get('series', [])
    out = {}
    for s in series:
        rnti = s.get('tags', {}).get('rnti', 'unknown')
        cols = s.get('columns', [])
        time_idx = cols.index('time') if 'time' in cols else 0
        val_idx = 1
        points = [
            {'t': row[time_idx], 'v': row[val_idx]}
            for row in s.get('values', [])
            if row[val_idx] is not None
        ]
        out[rnti] = points
    return out, None
