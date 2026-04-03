import requests
from django.conf import settings


def query(q: str) -> dict:
    """Execute InfluxQL query, return raw json."""
    try:
        r = requests.get(
            f'{settings.INFLUX_URL}/query',
            params={'db': settings.INFLUX_DB, 'q': q},
            timeout=3,
        )
        r.raise_for_status()
        return {'ok': True, 'data': r.json()}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def get_current_ue_stats():
    """Latest stats per UE (RNTI)."""
    q = 'SELECT last("dl_brate"), last("ul_brate"), last("cqi"), last("dl_mcs") FROM "ue" GROUP BY "rnti"'
    result = query(q)
    if not result['ok']:
        return None, result['error']
    series = result['data'].get('results', [{}])[0].get('series', [])
    ues = []
    for i, s in enumerate(series[:4]):
        vals = s.get('values', [[None]*5])[0]
        ues.append({
            'id': i + 1,
            'rnti': s.get('tags', {}).get('rnti', f'UE{i+1}'),
            'dl': round((vals[1] or 0) / 1e6, 2),
            'ul': round((vals[2] or 0) / 1e6, 2),
            'cqi': vals[3] or 0,
            'mcs': vals[4] or 0,
        })
    return ues, None


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
