#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  cat >&2 <<'EOF'
usage: watch_gepa_fallback_health.sh <screen_name> <gepa_log_path> <llama_log_path> [interval_seconds] [status_log_path]

Monitors:
- local llama.cpp decode speed (alert if sustained below floor)
- new "no textual output" warnings in GEPA log
- GEPA iteration stall
EOF
  exit 2
fi

SCREEN_NAME="$1"
GEPA_LOG_PATH="$2"
LLAMA_LOG_PATH="$3"
INTERVAL_SECONDS="${4:-180}"
STATUS_LOG_PATH="${5:-logs/gepa_fallback_health_${SCREEN_NAME}.log}"

# Alert policy defaults (override via env if needed)
TOKENS_FLOOR="${TOKENS_FLOOR:-40}"               # tok/s floor
TOKENS_WINDOW="${TOKENS_WINDOW:-12}"             # recent eval lines
TOKENS_BELOW_MIN="${TOKENS_BELOW_MIN:-8}"        # must be below floor in >= N lines
STALL_CHECKS="${STALL_CHECKS:-8}"                # unchanged iteration checks before alert

mkdir -p "$(dirname "$STATUS_LOG_PATH")"

ts() {
  date +"%Y-%m-%d %H:%M:%S %Z"
}

is_screen_active() {
  screen -ls | rg -q "\\.${SCREEN_NAME}[[:space:]]"
}

notify_user() {
  local title="$1"
  local body="$2"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "$title" "$body" || true
  fi
}

latest_iter_line() {
  if [[ ! -f "$GEPA_LOG_PATH" ]]; then
    echo "gepa-log-missing"
    return
  fi
  rg -N "Iteration [0-9]+: Selected program [0-9]+ score:" "$GEPA_LOG_PATH" | tail -n 1
}

latest_iter_id() {
  local line
  line="$(latest_iter_line)"
  if [[ "$line" == "gepa-log-missing" || -z "$line" ]]; then
    echo ""
    return
  fi
  sed -E 's/.*Iteration ([0-9]+):.*/\1/' <<<"$line"
}

latest_no_text_line_number() {
  if [[ ! -f "$GEPA_LOG_PATH" ]]; then
    echo 0
    return
  fi
  local match
  match="$(rg -n "Responses API returned no textual output|returned no text|returned no textual output|returned no text output" "$GEPA_LOG_PATH" | tail -n 1 || true)"
  if [[ -z "$match" ]]; then
    echo 0
  else
    cut -d: -f1 <<<"$match"
  fi
}

recent_tps_stats() {
  if [[ ! -f "$LLAMA_LOG_PATH" ]]; then
    echo "llama-log-missing"
    return
  fi
  local lines
  lines="$(
    rg "^[[:space:]]*eval time =" "$LLAMA_LOG_PATH" \
      | tail -n "$TOKENS_WINDOW" \
      | sed -E 's/.* ([0-9]+(\.[0-9]+)?) tokens per second.*/\1/' \
      | rg '^[0-9]+(\.[0-9]+)?$' || true
  )"
  if [[ -z "$lines" ]]; then
    echo "no-eval-lines"
    return
  fi
  awk -v floor="$TOKENS_FLOOR" '
    BEGIN{n=0;below=0;sum=0;min=1e9;max=0}
    {
      x=$1+0;
      n++;
      sum+=x;
      if (x<min) min=x;
      if (x>max) max=x;
      if (x<floor) below++;
    }
    END{
      if(n==0){print "no-eval-lines"; exit}
      printf "n=%d below=%d mean=%.2f min=%.2f max=%.2f", n, below, sum/n, min, max
    }
  ' <<<"$lines"
}

last_iter_id=""
stall_count=0
last_no_text_line="$(latest_no_text_line_number)"
if ! [[ "$last_no_text_line" =~ ^[0-9]+$ ]]; then
  last_no_text_line=0
fi
slow_alert_armed=1
stall_alert_armed=1

{
  echo "[$(ts)] watch-start screen=${SCREEN_NAME} interval_s=${INTERVAL_SECONDS} floor=${TOKENS_FLOOR} window=${TOKENS_WINDOW} below_min=${TOKENS_BELOW_MIN}"
  echo "[$(ts)] gepa_log=${GEPA_LOG_PATH}"
  echo "[$(ts)] llama_log=${LLAMA_LOG_PATH}"
} >>"$STATUS_LOG_PATH"

notify_user "GEPA Fallback Health Watch Started" "Monitoring ${SCREEN_NAME} local fallback speed and response quality."

while true; do
  now="$(ts)"

  if ! is_screen_active; then
    echo "[$now] screen-inactive; final_iter=$(latest_iter_id)" >>"$STATUS_LOG_PATH"
    notify_user "GEPA Watch Stopped" "${SCREEN_NAME} no longer active."
    break
  fi

  iter_id="$(latest_iter_id)"
  iter_line="$(latest_iter_line)"

  if [[ -n "$iter_id" && "$iter_id" == "$last_iter_id" ]]; then
    stall_count=$((stall_count + 1))
  else
    stall_count=0
    last_iter_id="$iter_id"
    stall_alert_armed=1
  fi

  tps_stats="$(recent_tps_stats)"
  no_text_latest="$(latest_no_text_line_number)"

  below_count=0
  if [[ "$tps_stats" =~ below=([0-9]+) ]]; then
    below_count="${BASH_REMATCH[1]}"
  fi

  echo "[$now] iter=${iter_id:-na} stall_checks=${stall_count} tps=${tps_stats} no_text_line=${no_text_latest}" >>"$STATUS_LOG_PATH"

  if [[ "$below_count" -ge "$TOKENS_BELOW_MIN" && "$slow_alert_armed" -eq 1 ]]; then
    notify_user "GEPA Fallback Slow" "${SCREEN_NAME}: local tok/s sustained below ${TOKENS_FLOOR}. See ${STATUS_LOG_PATH}"
    echo "[$now] ALERT slow-fallback ${tps_stats}" >>"$STATUS_LOG_PATH"
    slow_alert_armed=0
  fi
  if [[ "$below_count" -lt "$TOKENS_BELOW_MIN" ]]; then
    slow_alert_armed=1
  fi

  if [[ "$stall_count" -ge "$STALL_CHECKS" && "$stall_alert_armed" -eq 1 ]]; then
    notify_user "GEPA Potential Stall" "${SCREEN_NAME}: iteration unchanged for ${stall_count} checks."
    echo "[$now] ALERT stall iter=${iter_id:-na} checks=${stall_count} line=${iter_line}" >>"$STATUS_LOG_PATH"
    stall_alert_armed=0
  fi

  if [[ "$no_text_latest" -gt "$last_no_text_line" ]]; then
    new_count=$((no_text_latest - last_no_text_line))
    notify_user "GEPA No-Text Warning" "${SCREEN_NAME}: new no-text response warning(s) detected."
    echo "[$now] ALERT no-text new_entries~${new_count} latest_line=${no_text_latest}" >>"$STATUS_LOG_PATH"
    last_no_text_line="$no_text_latest"
  fi

  sleep "$INTERVAL_SECONDS"
done
