#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <screen_name> <run_log_path> [interval_seconds] [status_log_path]" >&2
  exit 2
fi

SCREEN_NAME="$1"
RUN_LOG_PATH="$2"
INTERVAL_SECONDS="${3:-3600}"
STATUS_LOG_PATH="${4:-logs/gepa_watch_${SCREEN_NAME}.log}"

mkdir -p "$(dirname "$STATUS_LOG_PATH")"

ts() {
  date +"%Y-%m-%d %H:%M:%S %Z"
}

is_screen_active() {
  screen -ls | rg -q "\\.${SCREEN_NAME}[[:space:]]"
}

extract_progress() {
  if [[ ! -f "$RUN_LOG_PATH" ]]; then
    echo "run-log-missing"
    return
  fi
  local progress
  progress="$(
    tail -n 600 "$RUN_LOG_PATH" \
      | rg -N "GEPA Optimization:|^Iteration [0-9]+:" \
      | tail -n 2 \
      | tr '\n' ' ' \
      | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//'
  )"
  if [[ -z "$progress" ]]; then
    echo "progress-unavailable"
  else
    echo "$progress"
  fi
}

notify_user() {
  local title="$1"
  local body="$2"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "$title" "$body" || true
  fi
}

{
  echo "[$(ts)] watch-start screen=${SCREEN_NAME} interval_s=${INTERVAL_SECONDS} run_log=${RUN_LOG_PATH}"
  if is_screen_active; then
    echo "[$(ts)] initial-status running; next check in ${INTERVAL_SECONDS}s"
  else
    echo "[$(ts)] initial-status not-running"
  fi
} >>"$STATUS_LOG_PATH"

notify_user "GEPA Watch Started" "Watching ${SCREEN_NAME}; first reminder in ${INTERVAL_SECONDS}s."

while true; do
  sleep "$INTERVAL_SECONDS"
  now="$(ts)"
  if is_screen_active; then
    next="$(date -d "+${INTERVAL_SECONDS} seconds" +"%Y-%m-%d %H:%M:%S %Z")"
    progress="$(extract_progress)"
    line="[$now] running; progress=${progress}; next_check=${next}"
    echo "$line" >>"$STATUS_LOG_PATH"
    notify_user "GEPA Still Running" "${SCREEN_NAME} is running. Next check at ${next}."
  else
    line="[$now] finished-or-stopped; final_progress=$(extract_progress)"
    echo "$line" >>"$STATUS_LOG_PATH"
    notify_user "GEPA Watch Done" "${SCREEN_NAME} is no longer running."
    break
  fi
done

