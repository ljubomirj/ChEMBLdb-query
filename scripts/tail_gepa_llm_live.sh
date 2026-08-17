#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  tail_gepa_llm_live.sh [options]

Watch the latest GEPA per-case LLM outputs (pf_up/pf_sql raw_text) in near real-time.

Options:
  --run-dir PATH        GEPA run directory. If omitted, newest gepa_v5_* under --eval-root is used.
  --eval-root PATH      Parent directory containing gepa_v5_* runs.
                        Default: /opt/ljubomir/ChEMBLdb-query/runs
  --step STEP           Which step artifacts to watch: up | sql | both (default: both)
  --lines N             Show last N lines of raw text (default: 120)
  --interval SEC        Poll interval seconds (default: 1)
  --no-clear            Do not clear screen when a new artifact appears.
  -h, --help            Show this help.

Examples:
  scripts/tail_gepa_llm_live.sh
  scripts/tail_gepa_llm_live.sh --step sql --interval 2
  scripts/tail_gepa_llm_live.sh --run-dir runs/gepa_v5_...
EOF
}

EVAL_ROOT="/opt/ljubomir/ChEMBLdb-query/runs"
RUN_DIR=""
STEP="both"
LINES=120
INTERVAL=1
NO_CLEAR=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --run-dir)
            RUN_DIR="${2:-}"
            shift 2
            ;;
        --eval-root)
            EVAL_ROOT="${2:-}"
            shift 2
            ;;
        --step)
            STEP="${2:-}"
            shift 2
            ;;
        --lines)
            LINES="${2:-}"
            shift 2
            ;;
        --interval)
            INTERVAL="${2:-}"
            shift 2
            ;;
        --no-clear)
            NO_CLEAR=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$STEP" in
    up|sql|both) ;;
    *)
        echo "Invalid --step: $STEP (expected up|sql|both)" >&2
        exit 2
        ;;
esac

if ! [[ "$LINES" =~ ^[0-9]+$ ]] || [[ "$LINES" -lt 1 ]]; then
    echo "Invalid --lines: $LINES" >&2
    exit 2
fi

if ! [[ "$INTERVAL" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "Invalid --interval: $INTERVAL" >&2
    exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "This script requires jq in PATH." >&2
    exit 127
fi

resolve_run_dir() {
    if [[ -n "$RUN_DIR" ]]; then
        if [[ ! -d "$RUN_DIR" ]]; then
            echo "Run dir not found: $RUN_DIR" >&2
            exit 1
        fi
        echo "$RUN_DIR"
        return
    fi

    local newest
    newest="$(
        find "$EVAL_ROOT" -maxdepth 1 -mindepth 1 -type d -name 'gepa_v5_*' -printf '%T@ %p\n' 2>/dev/null \
        | sort -n \
        | tail -n 1 \
        | cut -d' ' -f2-
    )"
    if [[ -z "$newest" ]]; then
        echo "No gepa_v5_* run dirs found under: $EVAL_ROOT" >&2
        exit 1
    fi
    echo "$newest"
}

latest_artifact() {
    local run="$1"
    local -a patterns=()
    case "$STEP" in
        up) patterns=(-name 'pf_up.output.json') ;;
        sql) patterns=(-name 'pf_sql.output.json') ;;
        both) patterns=(-name 'pf_up.output.json' -o -name 'pf_sql.output.json') ;;
    esac

    find "$run/candidate_evals" -type f \( "${patterns[@]}" \) -printf '%T@ %p\n' 2>/dev/null \
    | sort -n \
    | tail -n 1 \
    | cut -d' ' -f2-
}

render_artifact() {
    local file="$1"
    local now
    now="$(date '+%Y-%m-%d %H:%M:%S %Z')"
    local rel="${file#"$RUN_DIR"/}"

    echo "[$now] run: $RUN_DIR"
    echo "artifact: $rel"
    jq -r '
      "step: \(.selected_step // "-")",
      "case: \(.corpus // "-")/\(.case_id // "-") split=\(.split // "-") family=\(.family // "-")",
      "provider: \(.execution.provider // "-") model=\(.execution.model // "-") base=\(.execution.base_url // "-")",
      "--- raw_text ---"
    ' "$file"
    jq -r '
      if .execution.raw_text != null then .execution.raw_text
      elif .execution.parsed_json != null then ("<execution.parsed_json>\n" + (.execution.parsed_json | tostring))
      elif .up_exec != null then ("<up_exec>\n" + (.up_exec | tostring))
      elif .sql != null then ("<sql>\n" + (.sql | tostring))
      else "<no execution text payload>"
      end
    ' "$file" | tail -n "$LINES"
}

RUN_DIR="$(resolve_run_dir)"
if [[ ! -d "$RUN_DIR/candidate_evals" ]]; then
    echo "No candidate_evals directory yet: $RUN_DIR/candidate_evals" >&2
    exit 1
fi

last_file=""
while true; do
    file="$(latest_artifact "$RUN_DIR")"
    if [[ -n "$file" && "$file" != "$last_file" ]]; then
        if [[ "$NO_CLEAR" -eq 0 ]]; then
            clear
        fi
        render_artifact "$file"
        last_file="$file"
    else
        printf '\r[%s] waiting... latest=%s' "$(date '+%H:%M:%S')" "${last_file:-none}"
    fi
    sleep "$INTERVAL"
done
