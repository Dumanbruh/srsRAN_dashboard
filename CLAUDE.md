# srsRAN Dashboard — Контекст для Claude

## Цель проекта
Django-дашборд мониторинга srsRAN 5G NR testbed.
Метрики: InfluxDB (v2 с v1-compat). Управление каналом: GNU Radio XML-RPC. AI анализ: Ollama.

## Архитектура

```
Open5GS (AMF 127.0.0.5:38412, UPF ogstun 10.45.0.1)
    ↕ N2/N3
gNB (srsRAN Project, ZMQ) ── ws://127.0.0.1:8001 (JSON metrics) ──▶ metrics_bridge.py
    ↕ ZMQ tcp://127.0.0.1:2000/2001
GNU Radio broker (multi_ue_1_nogui.py) ── XML-RPC :8080 ◀── Django gnuradio.py
    ↕ ZMQ tcp://127.0.0.1:2100/2101
srsUE (netns: ue1, IMSI 999700000000001, PLMN 99970)
    ↕ tun_srsue
iperf3 / ping трафик для реальных CQI/MCS метрик

metrics_bridge.py ──▶ InfluxDB v2.8 /write?db=srsran (v1-compat endpoint)
Django dashboard  ──▶ InfluxDB v2.8 /query?db=srsran (v1-compat endpoint)
Django dashboard  ──▶ Ollama :11434 /api/generate
```

## Ключевые файлы

| Файл | Назначение |
|---|---|
| `dashboard/influx.py` | InfluxQL клиент (v1 compat). Читает measurement `ue`, tag `rnti`, поля: `dl_brate`, `ul_brate`, `cqi`, `dl_mcs`, `ul_mcs`, `dl_nof_nok`, `ul_nof_nok` |
| `dashboard/gnuradio.py` | XML-RPC клиент к GNU Radio (:8080/RPC2). Методы: `set_ue{N}_path_loss_db`, `set_noise_level` (алиасы в брокере) |
| `dashboard/views.py` | Django views + `api_ai_insight` endpoint (POST /api/ai/insight/) |
| `metrics_bridge.py` | WebSocket → InfluxDB bridge. ws://127.0.0.1:8001 → /write?db=srsran |
| `start_testbed.sh` | Стартовый скрипт (GNU Radio → gNB → UE → bridge) |
| `../fix_open5gs_net.sh` | Исправляет AMF/UPF IP и добавляет loopback alias 127.0.0.5 |
| `../ue_simulation_v3/multi_ue_1_nogui.py` | GNU Radio брокер (headless, 1 UE, XML-RPC :8080) |
| `../ue_simulation_v3/configs/gnb_zmq.yml` | gNB конфиг: ZMQ, metrics WS :8001, remote_control :8001 |
| `../ue_simulation_v3/configs/ue_zmq.conf` | srsUE конфиг: ZMQ порты 2100/2101, Band 3, 5 MHz |

## InfluxDB

- **Сервер**: InfluxDB v2.8.0 (НЕ v1), но с v1-compat endpoint
- **URL**: http://localhost:8086
- **Org**: srsran (ID: fa40ca8f7b01f4fc)
- **Bucket**: srsran (ID: ffa25d2d7e1b77ae)
- **Token**: см. `INFLUX_TOKEN` в `.env` (не хранится в репозитории)
- **Auth**: `Authorization: Token ...` заголовок на `/query` и `/write`
- **DBRP маппинг**: db=srsran → bucket srsran (ID: 10f271d55adf0000)
- **ВАЖНО**: НЕ менять на v2 API в influx.py. НЕ менять схему измерений.

## GNU Radio ZMQ порты (1 UE)

| Порт | Направление | Описание |
|---|---|---|
| tcp://127.0.0.1:2000 | gNB TX → GNU Radio | DL от gNB |
| tcp://127.0.0.1:2001 | GNU Radio → gNB RX | UL к gNB |
| tcp://127.0.0.1:2100 | GNU Radio → UE RX | DL к UE1 |
| tcp://127.0.0.1:2101 | UE TX → GNU Radio | UL от UE1 |

## XML-RPC методы (GNU Radio broker :8080)

- `set_ue1_path_loss_db(float)` — pathloss UE1 в dB (0–100)
- `get_ue1_path_loss_db()` → float
- `set_ue1_noise_amp(float)` — AWGN amplitude (0.0–0.01)
- `set_noise_level(float)` / `set_fading_level` / `set_shadowing_level` / `set_doppler_level` / `set_interference_level` — алиасы → `set_ue1_noise_amp`
- `get_all_path_losses()` → dict
- `get_samp_rate()` → int (5760000)

## Open5GS

- AMF NGAP: 127.0.0.5:38412 (после запуска fix_open5gs_net.sh)
- UPF GTP-U: 127.0.0.5 (N3)
- UPF tunnel: ogstun / 10.45.0.1/16
- Subscriber IMSI: 999700000000001, PLMN 99970, TAC 1
- K: 465b5ce8b199b49faa5f0a2ee238a6bc, OPC: e8ed289deba952e4283b54e88e6183ca

## Порядок запуска

```bash
# 1. Один раз (если AMF/UPF на старом IP или нет loopback alias)
sudo bash /home/user/fix_open5gs_net.sh

# 2. Dashboard + Ollama
cd /home/user/srsRAN_dashboard
docker compose up -d
docker exec srsran_ollama ollama pull qwen2.5:7b-instruct  # первый раз

# 3. Testbed
bash /home/user/srsRAN_dashboard/start_testbed.sh start

# 4. Трафик (после подключения UE, ~15 сек)
sudo ip netns exec ue1 iperf3 -c 10.45.0.1 -t 60

# 5. Статус
bash /home/user/srsRAN_dashboard/start_testbed.sh status
```

## Известные ограничения / подводные камни

1. InfluxDB v2 маскируется под v1 через compat endpoint — не менять на нативный v2 API
2. AMF/UPF были настроены на 10.1.16.168 (старый IP) — нужен fix_open5gs_net.sh
3. GNU Radio требует X11 для GUI-версий (multi_ue_scenario.py) — используем multi_ue_1_nogui.py
4. gNB метрики идут через WebSocket на порту 8001 (remote_control), не через штатный metrics_server (который пишет в InfluxDB v2 напрямую и несовместим)
5. gNB N3 (GTP-U) bind_addr = **127.0.0.2** — UPF уже занял 127.0.0.5:2152, нельзя конфликтовать
6. После `docker compose build` нужен `docker compose up -d web` — build только пересобирает образ, контейнер сам не перезапускается
5. AI endpoint /api/ai/insight/ работает только когда в InfluxDB есть данные UE
6. srsUE нужен namespace ue1: `sudo ip netns add ue1` (делается в start_testbed.sh)
