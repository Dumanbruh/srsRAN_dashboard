#!/usr/bin/env python3
"""
metrics_bridge.py — gNB JSON WebSocket → InfluxDB v1-compat writer.

Connects to srsRAN Project gNB remote_control WebSocket (port 8001),
parses per-UE JSON metrics, writes to InfluxDB measurement "ue" with
the exact fields and tag expected by dashboard/influx.py:

  measurement: ue
  tag:         rnti
  fields:      dl_brate, ul_brate, cqi, dl_mcs, ul_mcs, dl_nof_nok, ul_nof_nok,
               dl_nof_ok, ul_nof_ok, snr
"""

import os
import json
import time
import logging
import requests
import websocket
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [bridge] %(levelname)s %(message)s',
)
log = logging.getLogger(__name__)

INFLUX_URL   = os.environ.get('INFLUX_URL', 'http://127.0.0.1:8086')
INFLUX_DB    = os.environ.get('INFLUX_DB', 'srsran')
INFLUX_TOKEN = os.environ.get('INFLUX_TOKEN', '')
GNB_WS_URL   = 'ws://127.0.0.1:8001'

WRITE_URL    = f'{INFLUX_URL}/write'
AUTH_HEADERS = {'Authorization': f'Token {INFLUX_TOKEN}'}

RECONNECT_DELAY = 5   # seconds between reconnect attempts


def parse_and_write(raw: str) -> None:
    """Parse one gNB JSON metrics frame and write to InfluxDB."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning('JSON parse error: %s', e)
        return

    # srsRAN Project scheduler JSON metrics format (gnb 25.10.0):
    # { "timestamp": ..., "cells": [ { "cell_metrics": {...}, "ue_list": [
    #   { "rnti": 17921, "cqi": 15, "dl_brate": 0.0, "dl_mcs": 0, "dl_nof_nok": 0,
    #     "ul_brate": 0.0, "ul_mcs": 0, "ul_nof_nok": 0, ... }, ... ] }, ... ] }
    ue_list = [ue for cell in data.get('cells', []) for ue in cell.get('ue_list', [])]
    if not ue_list:
        return

    lines = []
    ts_ns = int(time.time() * 1e9)

    for ue in ue_list:
        rnti = ue.get('rnti')
        if rnti is None:
            continue
        rnti_tag = f'0x{int(rnti):x}'

        cqi        = ue.get('cqi', 0)
        dl_brate   = float(ue.get('dl_brate',   0))
        ul_brate   = float(ue.get('ul_brate',   0))
        dl_mcs     = float(ue.get('dl_mcs',     0))
        ul_mcs     = float(ue.get('ul_mcs',     0))
        dl_nof_nok = float(ue.get('dl_nof_nok', 0))
        ul_nof_nok = float(ue.get('ul_nof_nok', 0))
        dl_nof_ok  = float(ue.get('dl_nof_ok',  0))
        ul_nof_ok  = float(ue.get('ul_nof_ok',  0))
        snr        = float(ue.get('pucch_snr_db', 0))

        line = (
            f'ue,rnti={rnti_tag} '
            f'dl_brate={dl_brate},ul_brate={ul_brate},'
            f'cqi={float(cqi)},dl_mcs={dl_mcs},ul_mcs={ul_mcs},'
            f'dl_nof_nok={dl_nof_nok},ul_nof_nok={ul_nof_nok},'
            f'dl_nof_ok={dl_nof_ok},ul_nof_ok={ul_nof_ok},snr={snr} '
            f'{ts_ns}'
        )
        lines.append(line)

    if not lines:
        return

    payload = '\n'.join(lines)
    try:
        r = requests.post(
            WRITE_URL,
            params={'db': INFLUX_DB, 'precision': 'ns'},
            headers=AUTH_HEADERS,
            data=payload,
            timeout=3,
        )
        if r.status_code == 204:
            log.info('Wrote %d UE(s): %s', len(lines),
                     [l.split(' ')[0] for l in lines])
        else:
            log.error('InfluxDB write error %d: %s', r.status_code, r.text[:200])
    except Exception as e:
        log.error('InfluxDB request failed: %s', e)


def on_message(ws, message):
    parse_and_write(message)


def on_error(ws, error):
    log.error('WebSocket error: %s', error)


def on_close(ws, code, msg):
    log.warning('WebSocket closed: %s %s', code, msg)


def on_open(ws):
    log.info('Connected to gNB metrics WebSocket at %s', GNB_WS_URL)
    ws.send(json.dumps({'cmd': 'metrics_subscribe'}))
    log.info('Sent metrics_subscribe command')


def run():
    while True:
        log.info('Connecting to %s ...', GNB_WS_URL)
        ws = websocket.WebSocketApp(
            GNB_WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever(ping_interval=20, ping_timeout=10)
        log.info('Reconnecting in %ds ...', RECONNECT_DELAY)
        time.sleep(RECONNECT_DELAY)


if __name__ == '__main__':
    run()
