#!/bin/bash
# testbed_root_ops.sh — root-only primitives for the testbed helper.
#
# MUST be owned root:root, mode 750, and invoked ONLY via the sudoers
# NOPASSWD entry set up for this exact path (see CLAUDE.md / setup docs).
# Do not make this file writable by the invoking user — the sudoers rule
# grants passwordless root execution of it, so it must not also be
# user-editable (that would be a privilege-escalation hole).
#
# Thin wrappers around existing tooling — does not reimplement UE/IMSI/port
# logic, delegates to launch_ues.sh.

set -euo pipefail

SIM_DIR=/home/user/ue_simulation_v3
GNB_BIN=/usr/local/bin/gnb
GNB_CONFIG="$SIM_DIR/configs/gnb_zmq.yml"
LOG_DIR=/tmp/testbed_logs
LAUNCH_UES="$SIM_DIR/scripts/launch_ues.sh"
SRSUE_BIN=/usr/local/bin/srsue
UE_CONFIG="$SIM_DIR/configs/ue_zmq.conf"

mkdir -p "$LOG_DIR"

gnb_start() {
    if screen -list 2>/dev/null | grep -q '\.gnb\b'; then
        echo "gnb already running"
        exit 0
    fi
    screen -dmS gnb bash -c "$GNB_BIN -c $GNB_CONFIG > $LOG_DIR/gnb.log 2>&1"
}

gnb_stop() {
    screen -S gnb -X quit 2>/dev/null || true
    pkill -f "$GNB_BIN" 2>/dev/null || true
}

gnb_status() {
    if screen -list 2>/dev/null | grep -q '\.gnb\b'; then
        echo running
    else
        echo stopped
    fi
}

ues_start() {
    local n="$1"
    SRSUE_BIN="$SRSUE_BIN" TEMPLATE_CONFIG="$UE_CONFIG" bash "$LAUNCH_UES" "$n"
}

ues_stop() {
    SRSUE_BIN="$SRSUE_BIN" TEMPLATE_CONFIG="$UE_CONFIG" bash "$LAUNCH_UES" stop
}

ues_status() {
    SRSUE_BIN="$SRSUE_BIN" TEMPLATE_CONFIG="$UE_CONFIG" bash "$LAUNCH_UES" status
}

netns_ip() {
    local i="$1"
    ip netns exec "ue$i" ip addr show 2>/dev/null | grep -oP 'inet \K10\.\d+\.\d+\.\d+' | head -1 || true
}

free_ports() {
    pkill -9 -f "multi_ue_" 2>/dev/null || true
    for port in 2000 2001 2100 2101 2200 2201 2300 2301 2400 2401 2500 2501 2600 2601 2700 2701; do
        fuser -k "${port}/tcp" 2>/dev/null || true
    done
}

run_iperf() {
    local i="$1"
    local dur="$2"
    if ! [[ "$i" =~ ^[0-9]+$ ]] || ! [[ "$dur" =~ ^[0-9]+$ ]] || [ "$dur" -lt 1 ] || [ "$dur" -gt 30 ]; then
        echo '{"error":"invalid ue id or duration"}'
        exit 1
    fi
    ip netns exec "ue$i" iperf3 -c 10.45.0.1 -p $((5200 + i)) -t "$dur" -b "${rate}M" -J "${rev_flag[@]}" 2>&1 || true
}

iperf_client() {
      local i="$1" dur="$2" rate="$3" rev="$4"
      if ! [[ "$i" =~ ^[0-9]+$ ]] || [ "$i" -lt 1 ] || [ "$i" -gt 7 ]; then
          echo '{"error":"invalid ue id"}'; exit 1
      fi
      if ! [[ "$dur" =~ ^[0-9]+$ ]] || [ "$dur" -lt 1 ] || [ "$dur" -gt 1800 ]; then
          echo '{"error":"invalid duration"}'; exit 1
      fi
      if ! [[ "$rate" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
          echo '{"error":"invalid bitrate"}'; exit 1
      fi
      local rev_flag=()
      if [ "$rev" = "1" ]; then
          rev_flag=(-R)
      elif [ "$rev" != "0" ]; then
          echo '{"error":"invalid reverse flag"}'; exit 1
      fi
      ip netns exec "ue$i" iperf3 -c 10.45.0.1 -p $((5200 + i)) -t "$dur" -b "${rate}M" -J "${rev_flag[@]}" 2>&1 || true
  }

case "${1:-}" in
      gnb_start|gnb_stop|gnb_status|free_ports|ues_stop|ues_status) "$1" ;;
      ues_start)  ues_start "$2" ;;
      netns_ip)   netns_ip "$2" ;;
      run_iperf)  run_iperf "$2" "$3" ;;
      iperf_client) iperf_client "$2" "$3" "$4" "$5" ;;
      *)
          echo "usage: $0 {gnb_start|gnb_stop|gnb_status|ues_start N|ues_stop|ues_status|netns_ip i|free_ports|run_iperf
  i dur|iperf_client i dur rate_mbps reverse}"
          exit 1
          ;;
  esac
