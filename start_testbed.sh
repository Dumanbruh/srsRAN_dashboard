#!/bin/bash
# start_testbed.sh — запуск полного testbed srsRAN + GNU Radio + N UE + metrics bridge
# Требует: open5gs уже запущен (systemctl), docker compose up -d для dashboard+ollama
#
# Порядок: GNU Radio брокер → gNB → N UE → metrics bridge → трафик iperf3
#
# ВАЖНО: НИКОГДА не запускай этот скрипт целиком через sudo!
#   Каждая операция, которой нужен root, уже эскалируется сама через
#   testbed_root_ops.sh (у него отдельный sudoers NOPASSWD на конкретный путь).
#   Если обернуть весь скрипт в sudo, сломается metrics_bridge (у root нет
#   ~/.local/websocket-client пользователя) и gnuradio (screen-сессии станут
#   root-owned и пропадут из обычного `screen -list`).
#
# Использование:
#   ./start_testbed.sh start [N]              — запустить всё (N UE, 1-7, по умолчанию 1)
#   ./start_testbed.sh stop                   — остановить всё
#   ./start_testbed.sh status                 — показать статус
#   ./start_testbed.sh component-start <name> [N]  — запустить один компонент
#   ./start_testbed.sh component-stop <name>       — остановить один компонент
#     <name>: gnuradio | gnb | ue | bridge
#
# Гранулярные component-start/component-stop добавлены для process manager'а
# дэшборда (testbed_helper.py) — под капотом та же логика, что и в cmd_start/
# cmd_stop, вынесенная в функции comp_*, чтобы не дублировать проверенный код.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SIM_DIR="$REPO_ROOT/ue_simulation_v3"
LOG_DIR="/tmp/testbed_logs"
BRIDGE_PY="$SCRIPT_DIR/metrics_bridge.py"
ROOT_OPS="$SCRIPT_DIR/testbed_root_ops.sh"
GEN_MULTI_UE="$SIM_DIR/scripts/gen_multi_ue.py"

if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

PYTHON="${PYTHON:-python3}"
MAX_N=7

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
info() { echo -e "${CYAN}[--]${NC}   $*"; }
warn() { echo -e "${YELLOW}[!!]${NC}   $*"; }
err()  { echo -e "${RED}[EE]${NC}   $*"; }

root_ops() { sudo "$ROOT_OPS" "$@"; }

ensure_log_dir() {
    mkdir -p "$LOG_DIR"
    # 1777: gnb.log/ue пишутся root'ом (через testbed_root_ops.sh), gnuradio.log/
    # bridge.log — обычным пользователем (screen-сессии ниже). Обоим нужна запись
    # в один каталог.
    chmod 1777 "$LOG_DIR" 2>/dev/null || true
}

# ── Компоненты ──────────────────────────────────────────────────────────────

comp_gnuradio_start() {
    local n="${1:-1}"
    GR_SCRIPT="$SIM_DIR/multi_ue_${n}_nogui.py"
    if [ ! -f "$GR_SCRIPT" ]; then
        info "Генерируем брокер для $n UE ..."
        (cd "$SIM_DIR" && "$PYTHON" "$GEN_MULTI_UE" "$n" --no-gui)
    fi

    if screen -list 2>/dev/null | grep -q "gnuradio"; then
        local running_n
        running_n="$(cat "$LOG_DIR/.gnuradio_n" 2>/dev/null || echo "")"
        if [ "$running_n" = "$n" ]; then
            warn "GNU Radio уже запущен для $n UE (screen: gnuradio)"
            return 0
        fi
        # Брокер уже работает, но для другого числа UE (например, остался с
        # предыдущего запуска на 1 UE) — молча оставлять его значило бы, что
        # UE2/UE3 пытаются подключиться к портам, которые никто не слушает,
        # и никогда не зарегистрируются. Перезапускаем под нужный n.
        warn "GNU Radio запущен для другого числа UE (было: ${running_n:-?}, нужно: $n) — перезапускаю"
        comp_gnuradio_stop
        sleep 1
    fi

    # gNB's ZMQ radio driver is bound to one specific GNU Radio broker process
    # for its whole lifetime. If gNB stayed running from an earlier session
    # while GNU Radio just got (re)started above (or wasn't running at all),
    # gNB is now talking to a dead ZMQ peer: UEs can still attach at NAS/RRC
    # (so wait_ready for "ue" happily passes) but never show up in gNB's own
    # metrics feed — the run "succeeds" and the dashboard graph is silently
    # empty for its whole duration, with no error anywhere. Force gNB to
    # restart too; every caller (cmd_start and every scenario) always starts
    # gNB again right after this function returns, so this is never a no-op
    # that leaves gNB down.
    if root_ops gnb_status | grep -q running; then
        warn "gNB был привязан к предыдущему GNU Radio — перезапускаю для ресинхронизации"
        root_ops gnb_stop
        sleep 1
    fi

    info "Освобождаем ZMQ-порты от предыдущих запусков ..."
    root_ops free_ports
    sleep 1
    info "Запускаем GNU Radio брокер ($n UE) ..."
    screen -dmS gnuradio bash -c \
        "$PYTHON $GR_SCRIPT > $LOG_DIR/gnuradio.log 2>&1"
    # Порт 8080 — это XML-RPC сервер самого брокера (стабильный признак,
    # в отличие от 2000/2001, которые может слушать сам gNB, а не GNU Radio).
    for i in $(seq 1 30); do
        if ss -tln 2>/dev/null | grep -q ":8080 "; then
            break
        fi
        sleep 1
    done
    if ! screen -list 2>/dev/null | grep -q "gnuradio"; then
        err "GNU Radio не запустился, см. $LOG_DIR/gnuradio.log"
        return 1
    fi
    echo "$n" > "$LOG_DIR/.gnuradio_n"
    ok "GNU Radio запущен (screen: gnuradio, log: $LOG_DIR/gnuradio.log)"
}

comp_gnuradio_stop() {
    screen -S gnuradio -X quit 2>/dev/null && ok "gnuradio stopped" || warn "gnuradio was not running"
    rm -f "$LOG_DIR/.gnuradio_n" 2>/dev/null || true
}

comp_gnb_start() {
    if root_ops gnb_status | grep -q running; then
        warn "gNB уже запущен (screen: gnb)"
        return 0
    fi
    info "Запускаем gNB ..."
    root_ops gnb_start
    sleep 3
    if ! root_ops gnb_status | grep -q running; then
        err "gNB не запустился, см. $LOG_DIR/gnb.log"
        return 1
    fi
    ok "gNB запущен (screen: gnb, log: $LOG_DIR/gnb.log)"
}

comp_gnb_stop() {
    root_ops gnb_stop && ok "gnb stopped" || warn "gnb was not running"
}

comp_ue_start() {
    local n="${1:-1}"
    info "Запускаем $n srsUE ..."
    root_ops ues_start "$n"

    info "Ждём подключения UE (до 60 сек) ..."
    attached=0
    for wait_i in $(seq 1 20); do
        attached=0
        for i in $(seq 1 "$n"); do
            ip=$(root_ops netns_ip "$i")
            if [ -n "$ip" ]; then
                attached=$((attached + 1))
            fi
        done
        if [ "$attached" -eq "$n" ]; then
            break
        fi
        sleep 3
    done
    ok "Подключено UE: $attached/$n"
}

comp_ue_stop() {
    root_ops ues_stop && ok "UE stopped" || warn "UE was not running"
}

IPERF_BASE_PORT=5201

# iperf3's own server is single-threaded per instance — it can only run ONE
# test at a time and rejects a second concurrent client with "the server is
# busy running a test. try again later." A single shared `iperf3 -s` (the
# original setup) meant only one UE out of N ever got real load in a
# multi-UE scenario, silently — every other UE's load_dl/load_ul attempt
# just failed per-UE (seen live: 3 of 4 UEs failed this way in a real
# bufferbloat run, only the 4th got traffic). Fix: one dedicated iperf3
# server per UE slot, ports 5201..5200+MAX_N — iperf_client (root_ops)
# targets port 5200+<ue id>, so each UE always gets its own server.
comp_iperf_servers_start() {
    local started=0
    for i in $(seq 1 "$MAX_N"); do
        local sname="iperf-ue$i" p=$((IPERF_BASE_PORT + i - 1))
        if screen -list 2>/dev/null | grep -q "\.$sname\b"; then
            continue
        fi
        screen -dmS "$sname" bash -c "iperf3 -s -p $p > $LOG_DIR/iperf3_ue${i}.log 2>&1"
        started=$((started + 1))
    done
    if [ "$started" -gt 0 ]; then
        sleep 1
        ok "iperf3-серверы запущены (порты $IPERF_BASE_PORT-$((IPERF_BASE_PORT + MAX_N - 1)), новых: $started)"
    fi
}

comp_iperf_servers_stop() {
    for i in $(seq 1 "$MAX_N"); do
        screen -S "iperf-ue$i" -X quit 2>/dev/null || true
    done
}

comp_bridge_start() {
    comp_iperf_servers_start
    if screen -list 2>/dev/null | grep -q "metrics_bridge"; then
        warn "metrics bridge уже запущен"
        return 0
    fi
    info "Запускаем metrics bridge ..."
    screen -dmS metrics_bridge bash -c \
        "$PYTHON $BRIDGE_PY > $LOG_DIR/bridge.log 2>&1"
    sleep 1
    ok "metrics bridge запущен (screen: metrics_bridge, log: $LOG_DIR/bridge.log)"
}

comp_bridge_stop() {
    screen -S metrics_bridge -X quit 2>/dev/null && ok "metrics_bridge stopped" || warn "metrics_bridge was not running"
    comp_iperf_servers_stop
}

# ── Полный стенд (не менялось по поведению — только вызывает comp_* по порядку) ──

cmd_start() {
    local n="${1:-1}"
    if ! [[ "$n" =~ ^[0-9]+$ ]] || [ "$n" -lt 1 ] || [ "$n" -gt "$MAX_N" ]; then
        err "N должно быть числом от 1 до $MAX_N (получено: $n)"
        exit 1
    fi

    ensure_log_dir

    # ── 1. Проверки ─────────────────────────────────────────────────────────
    info "Проверяем предусловия ..."
    ip addr show lo | grep -q "127.0.0.5" || {
        err "Нет loopback alias 127.0.0.5. Запусти: sudo bash fix_open5gs_net.sh"
        exit 1
    }
    ss -tlnp 2>/dev/null | grep -q "127.0.0.5:38412" || \
    cat /proc/net/sctp/eps 2>/dev/null | grep -q "38412" || {
        warn "AMF NGAP (38412) не слышен. Запусти fix_open5gs_net.sh если ещё не запускал."
    }

    # ── 2. GNU Radio брокер (N UE) ───────────────────────────────────────────
    comp_gnuradio_start "$n"

    # ── 3. gNB ──────────────────────────────────────────────────────────────
    comp_gnb_start

    # ── 4. N × srsUE ─────────────────────────────────────────────────────────
    comp_ue_start "$n"

    # ── 5. metrics bridge ────────────────────────────────────────────────────
    comp_bridge_start

    echo ""
    ok "Testbed запущен ($n UE, подключено $attached). Проверь трафик:"
    for i in $(seq 1 "$n"); do
        echo "  sudo ip netns exec ue$i iperf3 -c 10.45.0.1 -t 60"
    done
    echo ""
    echo "Logs: $LOG_DIR/"
    echo "Screen sessions (user): $(screen -list 2>/dev/null | grep -E 'gnuradio|metrics_bridge' | awk '{print $1}' | tr '\n' ' ')"
}

cmd_stop() {
    info "Останавливаем testbed ..."
    comp_bridge_stop
    comp_ue_stop
    comp_gnb_stop
    comp_gnuradio_stop
    ok "Done."
}

cmd_status() {
    echo "=== Screen sessions (user: gnuradio, metrics_bridge) ==="
    screen -list 2>/dev/null | grep -E "gnuradio|metrics_bridge" || echo "(none)"
    echo ""
    echo "=== gNB ==="
    root_ops gnb_status
    echo ""
    echo "=== UE ==="
    root_ops ues_status
    echo ""
    echo "=== InfluxDB: last UE rows ==="
    TOKEN="${INFLUX_TOKEN:-}"
    curl -s "http://localhost:8086/query?db=srsran&q=SELECT+last(%22dl_brate%22),last(%22cqi%22)+FROM+%22ue%22+GROUP+BY+%22rnti%22" \
      -H "Authorization: Token $TOKEN" | python3 -m json.tool 2>/dev/null || echo "(InfluxDB unreachable)"
}

cmd_component_start() {
    local comp="${1:-}"
    local n="${2:-1}"
    ensure_log_dir
    case "$comp" in
        gnuradio) comp_gnuradio_start "$n" ;;
        gnb)      comp_gnb_start ;;
        ue)       comp_ue_start "$n" ;;
        bridge)   comp_bridge_start ;;
        *) err "Неизвестный компонент: '$comp' (ожидается gnuradio|gnb|ue|bridge)"; exit 1 ;;
    esac
}

cmd_component_stop() {
    local comp="${1:-}"
    case "$comp" in
        gnuradio) comp_gnuradio_stop ;;
        gnb)      comp_gnb_stop ;;
        ue)       comp_ue_stop ;;
        bridge)   comp_bridge_stop ;;
        *) err "Неизвестный компонент: '$comp' (ожидается gnuradio|gnb|ue|bridge)"; exit 1 ;;
    esac
}

# Клиент iperf3 всегда запускается ВНУТРИ netns UE (root_ops iperf_client,
# ip netns exec) — сервер стоит на хосте без всяких привилегий (просто
# `iperf3 -s`, ту же схему пользователь уже проверил вручную). Направление
# выбирается флагом -R самого iperf3: без него — UL (UE шлёт), с ним — DL
# (UE принимает). Никакого сервера внутри netns UE не нужно ни для одного из
# направлений — именно это раньше не работало (сервер пытались поднять не в
# том месте).
cmd_ue_load() {
    local i="${1:-}"
    local dur="${2:-10}"
    local rate="${3:-10}"
    local direction="${4:-dl}"
    local rev
    case "$direction" in
        dl) rev=1 ;;
        ul) rev=0 ;;
        *) err "Направление должно быть dl или ul (получено: $direction)"; exit 1 ;;
    esac
    root_ops iperf_client "$i" "$dur" "$rate" "$rev"
}

case "${1:-help}" in
    start)            cmd_start "${2:-1}" ;;
    stop)              cmd_stop ;;
    status)            cmd_status ;;
    component-start)   cmd_component_start "${2:-}" "${3:-1}" ;;
    component-stop)    cmd_component_stop "${2:-}" ;;
    ue-load)           cmd_ue_load "${2:-}" "${3:-10}" "${4:-10}" "${5:-dl}" ;;
    *)
        echo "Использование: $0 {start [N]|stop|status|component-start <name> [N]|component-stop <name>|ue-load <ue_id> [dur_s] [rate_mbps] [dl|ul]}"
        echo "  N — число UE, 1-$MAX_N (по умолчанию 1)"
        echo "  <name> — gnuradio|gnb|ue|bridge"
        echo "  Перед запуском: sudo bash fix_open5gs_net.sh"
        ;;
esac
