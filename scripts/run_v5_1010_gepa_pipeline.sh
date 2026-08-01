#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

STAMP="${1:-$(date +%Y%m%d_%H%M%S)}"
SEED_PROMPT_PACK="experiments/evals/v5_forward_eval/gepa_v5_weakfamilies_glm47_reseed56d_20260406_011416/candidate_cache/candidate_56d01a91befd8d8a.yaml"
MANIFEST_ROOT="tests/v5_manifests_1010"
PROBE_SPLIT="experiments/case_splits_v5.1010_gepa_probe.json"
FULL_SPLIT="experiments/case_splits_v5.1010.json"
PROFILE="zai-glm47-local-fallbacks"
REFLECTION_FALLBACK="http://127.0.0.1:18081/v1"

mkdir -p logs experiments/evals/v5_forward_eval

echo "[v5.1010] stamp=${STAMP}"
echo "[v5.1010] step=repair_surfaces"
uv run python scripts/repair_v5_1010_surfaces.py \
  |& tee "logs/v5_1010_surface_repair_${STAMP}.log"

echo "[v5.1010] step=build_probe_split"
uv run python scripts/build_v5_1010_gepa_probe_split.py \
  |& tee "logs/v5_1010_probe_split_${STAMP}.log"

BASELINE_LABEL="v5_1010_probe_baseline_v512_${STAMP}"
echo "[v5.1010] step=probe_baseline label=${BASELINE_LABEL}"
uv run python scripts/evaluate_v5_forward.py \
  --prompt-pack "${SEED_PROMPT_PACK}" \
  --split-file "${PROBE_SPLIT}" \
  --split test \
  --manifest-root "${MANIFEST_ROOT}" \
  --eval-label "${BASELINE_LABEL}" \
  --multi-endpoint-profile "${PROFILE}" \
  --up-max-tokens 1200 \
  --sql-max-tokens 4000 \
  --print-summary \
  |& tee "logs/v5_1010_probe_baseline_${STAMP}.log"

PROBE_RUN_DIR="experiments/evals/v5_forward_eval/gepa_v5_1010_probe_${STAMP}"
echo "[v5.1010] step=stratified_gepa run_dir=${PROBE_RUN_DIR}"
uv run python experiments/gepa_optimize_prompt_pack_v5.py \
  --seed-prompt-pack "${SEED_PROMPT_PACK}" \
  --output-prompt-pack "${PROBE_RUN_DIR}/best_prompt_pack.yaml" \
  --split-file "${PROBE_SPLIT}" \
  --manifest-root "${MANIFEST_ROOT}" \
  --run-dir "${PROBE_RUN_DIR}" \
  --multi-endpoint-profile "${PROFILE}" \
  --max-metric-calls 180 \
  --parallel \
  --max-workers 4 \
  --reflection-fallback-base-url "${REFLECTION_FALLBACK}" \
  --reflection-fallback-model nemotron-cascade-2-30b-a3b \
  |& tee "logs/v5_1010_probe_gepa_${STAMP}.log"

GATE_OUT="experiments/v5.1010_gepa_probe_gate_${STAMP}.json"
echo "[v5.1010] step=gate_full_gepa gate=${GATE_OUT}"
uv run python scripts/gate_v5_1010_gepa_probe.py \
  --baseline-report "experiments/evals/v5_forward_eval/${BASELINE_LABEL}/report.json" \
  --gepa-summary "${PROBE_RUN_DIR}/summary.json" \
  --out "${GATE_OUT}" \
  |& tee "logs/v5_1010_probe_gate_${STAMP}.log"

FULL_RUN_DIR="experiments/evals/v5_forward_eval/gepa_v5_1010_full_${STAMP}"
echo "[v5.1010] step=full_gepa run_dir=${FULL_RUN_DIR}"
uv run python experiments/gepa_optimize_prompt_pack_v5.py \
  --seed-prompt-pack "${PROBE_RUN_DIR}/best_prompt_pack.yaml" \
  --output-prompt-pack "${FULL_RUN_DIR}/best_prompt_pack.yaml" \
  --split-file "${FULL_SPLIT}" \
  --manifest-root "${MANIFEST_ROOT}" \
  --run-dir "${FULL_RUN_DIR}" \
  --multi-endpoint-profile "${PROFILE}" \
  --max-metric-calls 1200 \
  --parallel \
  --max-workers 4 \
  --reflection-fallback-base-url "${REFLECTION_FALLBACK}" \
  --reflection-fallback-model nemotron-cascade-2-30b-a3b \
  |& tee "logs/v5_1010_full_gepa_${STAMP}.log"

echo "[v5.1010] complete full_run_dir=${FULL_RUN_DIR}"
