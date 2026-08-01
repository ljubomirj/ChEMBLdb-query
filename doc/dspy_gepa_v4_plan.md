# DSPy / GEPA Optimization Plan for v4

## Scope

The `v4` line is the optimization track. `v3` stays unchanged as the stable baseline.

Concrete files:
- runtime: `src/db_llm_query_v4.py`
- seed artifact: `experiments/prompt_pack_v4.0.yaml`
- fixed benchmark split: `experiments/case_splits_v4.0.json`
- evaluator: `experiments/evaluate_prompt_pack_v4.py`
- GEPA runner: `experiments/gepa_optimize_prompt_pack_v4.py`

## Mutable artifacts

The first prompt-pack version lives at `experiments/prompt_pack_v4.0.yaml` and currently controls:
- `about_block`
- `examples_block`
- `up_task_template`
- `sql_task_template`
- `judge_task_template`
- `prompt_hints_path`

The runtime loader is in `src/db_llm_query_v4.py`.

## Benchmark sets

Primary optimization benchmark:
- `tests/cases/faq_hq_cases.json`
- `tests/cases/web_scrape_hq_cases.json`

Optional expensive benchmark:
- `tests/cases/web_scrape_large_cases.json`

Promotion pool for future benchmark growth:
- `tests/cases/web_scrape2_cases.json`

## Objective

Optimize prompt-pack artifacts against result-set correctness, not self-judge agreement.

Primary metric:
- pass rate on executable cases

Secondary metrics:
- required-column coverage
- row-count agreement
- runtime / accidental over-broad query penalties

## Recommended split

Initial train/val/test split should be fixed and versioned.

Suggested first cut:
- train: 10-12 small/medium executable cases
- val: 4-6 small/medium executable cases
- test: 2-4 untouched executable cases
- large test: `web_scrape_large` only for periodic evaluation, not every inner-loop candidate

The current fixed split lives in `experiments/case_splits_v4.0.json`.

## Optimization order

1. Optimize `prompt_hints` behavior via the prompt pack and referenced hints file.
2. Optimize `examples_block`.
3. Optimize `up_task_template`.
4. Optimize `sql_task_template`.
5. Optimize `judge_task_template` only after the result-based benchmark is strong.
6. Optimize harness/config knobs only later.

## Evaluator contract for GEPA

Candidate:
- one prompt-pack artifact, serialized as YAML text

Evaluator returns:
- scalar score
- actionable side information (ASI)

ASI should include per failed case:
- UQ
- expected columns vs actual columns
- expected vs actual row counts
- sample row diffs
- generated UP
- generated SQL
- judge text
- short failure label when detectable

## Near-term implementation steps

1. Keep `v4.0` behavior matched to `v3`.
2. Use `experiments/evaluate_prompt_pack_v4.py` to score prompt-pack candidates on the fixed executable-case splits.
3. Use `experiments/gepa_optimize_prompt_pack_v4.py` to optimize the full YAML prompt pack with GEPA generalization mode.
4. Version prompt packs as `v4.1`, `v4.2`, ...
5. Promote richer `web_scrape2` cases into executable lanes before broad optimization.

## Commands

List available optimization splits:

```bash
uv run python experiments/evaluate_prompt_pack_v4.py --list-splits
```

Score an existing prompt pack against held-out fixture CSVs without live model calls:

```bash
uv run python experiments/evaluate_prompt_pack_v4.py --reuse-existing --split val
```

Run a live evaluation of the train split with `v4`:

```bash
uv run python experiments/evaluate_prompt_pack_v4.py \
  --split train \
  --prompt-pack-path experiments/prompt_pack_v4.0.yaml \
  -- \
  --multi-endpoint-profile zai-pony-alpha-2
```

Start a GEPA optimization run:

```bash
uv run python experiments/gepa_optimize_prompt_pack_v4.py \
  --seed-prompt-pack experiments/prompt_pack_v4.0.yaml \
  --output-prompt-pack experiments/prompt_pack_v4.1.yaml \
  -- \
  --multi-endpoint-profile zai-pony-alpha-2
```
