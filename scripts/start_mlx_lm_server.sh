#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
MODEL_REL_DEFAULT="LMStudio_models/mlx-community/GLM-4.7-Flash-6bit"
MODEL_REL="${MODEL_REL:-$MODEL_REL_DEFAULT}"
CHAT_TEMPLATE="${CHAT_TEMPLATE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"; shift 2 ;;
    --port)
      PORT="$2"; shift 2 ;;
    --log-level)
      LOG_LEVEL="$2"; shift 2 ;;
    --model-rel)
      MODEL_REL="$2"; shift 2 ;;
    --chat-template)
      CHAT_TEMPLATE="$2"; shift 2 ;;
    *)
      echo "Unknown arg: $1" >&2
      echo "Usage: $0 [--host HOST] [--port PORT] [--log-level LEVEL] [--model-rel PATH] [--chat-template PATH]" >&2
      exit 1 ;;
  esac
done

cd "$HOME"

MLX_BIN="$HOME/LJ-ML-comp/mlx-lm/.venv/bin/mlx_lm.server"
if [[ ! -x "$MLX_BIN" ]]; then
  MLX_BIN="mlx_lm.server"
fi

ARGS=(--model "$MODEL_REL" --host "$HOST" --port "$PORT" --log-level "$LOG_LEVEL" --max-tokens 1024 --max-kv-size 4096 --kv-bits 8 --prompt-cache-size 1)
if [[ -n "$CHAT_TEMPLATE" ]]; then
  ARGS+=(--chat-template "$CHAT_TEMPLATE")
fi

echo "Starting mlx_lm.server with model: $MODEL_REL"
echo "Host: $HOST  Port: $PORT  Log level: $LOG_LEVEL"
set -x; exec "$MLX_BIN" "${ARGS[@]}"

