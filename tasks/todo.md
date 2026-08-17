# Tiny GEPA Run Plan (v5.1010)

- [x] Inspect repo status and confirm latest benchmark docs (`README.LJ`, `tests/README.md`, v5.1010 artifacts).
- [x] Verify runtime setup (Z.AI auth vars and local fallback endpoint/model on `127.0.0.1:8081`).
- [x] Create a tiny stratified subset split from `experiments/case_splits_v5.1010.json`.
- [x] Run tiny baseline evaluation on the subset test split.
- [x] Run one small GEPA optimization on the same subset.
- [x] Compare baseline vs GEPA held-out test metrics and summarize decision.
- [x] Append interaction summary to `MEMORY.md`.
- [x] Document any friction/signposts in `LEARNINGS.md` (only if encountered).

## Review

- Tiny24 baseline (seed `v5.0`) and tiny24 GEPA were completed.
- On tiny24 held-out test (6 cases), baseline `v5.0` was `1/6` pass (`0.166667`, mean `0.724826`), and the GEPA-selected candidate evaluated at `3/6` pass (`0.500000`, mean `0.916492`).
- The best GEPA candidate hash in that run stayed at the seed hash, so no prompt mutation was promoted despite metric gain.
- Added a targeted hard-case split for next short optimization cycle: `experiments/case_splits_v5.1010_gepa_tiny12_hard.json`.

## GEPA Post-Run Skill

- [x] Confirm exact runtime for `gepa_v5_1010_tiny24_from_v50_20260426_232232`.
- [x] Create new skill scaffold `.codex/skills/gepa-run-report/`.
- [x] Implement standard post-GEPA ops reporter script.
- [x] Validate script against tiny24 GEPA run and emit markdown/json report.
- [x] Validate skill structure with `quick_validate.py`.

### GEPA Post-Run Skill Review

- Added skill: `.codex/skills/gepa-run-report/SKILL.md`.
- Added script: `.codex/skills/gepa-run-report/scripts/post_gepa_report.py`.
- Added UI metadata: `.codex/skills/gepa-run-report/agents/openai.yaml`.
- Generated report example:
  `experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/post_gepa_ops_report.{md,json}`.

## Salts act.tid Fix A/B Plan (2026-04-27)

- [x] Build salts-only split from `experiments/case_splits_v5.1010_gepa_probe.json`.
- [x] Create patched prompt pack from candidate `8316c7a17406c0ce` with explicit `assays.tid` join rule.
- [x] Run baseline eval on salts-only split (current best candidate).
- [x] Run patched eval on salts-only split (new prompt pack).
- [x] Compare pass-rate and mean-score deltas and summarize.

### Salts act.tid Fix A/B Review

- Split used: `experiments/case_splits_v5.1010_gepa_probe_salts_only.json` (`train=6`, `val=2`, `test=4`, total `12`).
- Baseline eval:
  `experiments/evals/v5_forward_eval/v5_1010_probe_salts_ab_baseline_8316_20260427_232558/report.json`
  summary: `4/12` pass (`0.333333`), mean score `0.404167`.
- Patched eval:
  `experiments/evals/v5_forward_eval/v5_1010_probe_salts_ab_patched_acttidfix_20260427_232829/report.json`
  summary: `9/12` pass (`0.750000`), mean score `0.962500`.
- SQL pattern check:
  baseline had `7` SQLs with `td.tid = act.tid`; patched had `0`.
  baseline had `5` SQLs with `td.tid = a.tid`; patched had `10`.
- Delta from the patch on salts-only A/B: `+5` pass cases, `+0.416667` pass rate, `+0.558333` mean score.

## Long GEPA Run Plan (2026-04-28)

- [x] Validate local fallback endpoint health (`127.0.0.1:8081`) and model availability.
- [x] Confirm Z.AI Anthropic env vars are present for primary `glm-4.7`.
- [x] Launch long GEPA run from `experiments/prompt_pack_v5.10.yaml` on `experiments/case_splits_v5.1010_gepa_probe.json` with `8081`-only fallback.
- [x] Capture launch metadata (screen name, run dir, log path, budget settings).
- [x] Monitor early run progress (startup + rolling Z.AI cache-hit traffic observed; fallback endpoint pre-probed healthy).
- [ ] Run default post-run report skill when complete.
- [x] Start an hourly run-watch reminder loop that re-checks every hour while the run is active.

### Long GEPA Launch Metadata

- screen: `gepa8h_20260428_001211_r2400`
- run dir: `experiments/evals/v5_forward_eval/gepa_v5_1010_probe_long8h_v510_zai47_8081fb_20260428_001211`
- log: `logs/gepa_v5_1010_probe_long8h_v510_zai47_8081fb_20260428_001211.log`
- seed prompt pack: `experiments/prompt_pack_v5.10.yaml`
- split: `experiments/case_splits_v5.1010_gepa_probe.json` (`train=58`, `val=20`, `test=30`)
- budget/config: `--max-metric-calls 2400 --parallel --max-workers 3 --timeout 300 --reflection-minibatch-size 2`
- provider routing: primary `zai-anthropic/glm-4.7`, fallback `llamacpp@http://127.0.0.1:8081` model `qwen3.6-35b-a3b`

### Hourly Watcher

- watcher screen: `gepa_watch_hourly_20260428_0019`
- target run screen: `gepa8h_20260428_001211_r2400`
- watcher script: `scripts/watch_gepa_hourly.sh`
- watcher log: `logs/gepa_watch_gepa8h_20260428_001211_r2400.log`
- behavior: sleeps 1 hour, checks target screen, logs progress, then schedules the next 1-hour check by continuing the loop while active.

## Per-Case Harness Logs (2026-04-29)

- [x] Add per-case `.log` emission to `scripts/evaluate_v5_forward.py`.
- [x] Run a one-case smoke evaluation to verify `run.log` is created in the case artifact directory.
- [x] Summarize emitted log format and event sequence for future offline `.zstd` compression.

### Per-Case Harness Logs Review

- Harness now writes two case-local logs next to per-case artifacts.
- `run.log` is the human-readable transcript for `less`: case metadata, original UQ, prompt sections, raw model responses, parsed UP/SQL, SQL execution, deterministic score, and a bounded CSV preview.
- `run.events.jsonl` is the sparse machine-readable event stream with `case_start`, `step_start`/`step_done`, `case_complete`, `case_error`, or `case_reused_existing`.
- Smoke run label: `smoke_case_transcript_20260429_1case` produced:
  `experiments/evals/v5_forward_eval/smoke_case_transcript_20260429_1case/test/web_scrape_hq/afatinib_egfr_ic50_salts/run.log`.

## Judge-Loop Per-Case Transcript Logs (2026-04-29)

- [x] Add case-local `run.log` and `run.events.jsonl` emission to `scripts/evaluate_v5_forward_judge_loop.py`.
- [x] Include case metadata, original UQ, docs, prompt-pack sections, runtime stage log, accepted judge-loop iterations, final deterministic score, and bounded CSV preview.
- [x] Capture the live runtime log during `llm.query(...)` so failed parser/SQL attempts are preserved even when they are not exposed as accepted `Iteration` objects.
- [x] Run a one-case judge-loop smoke to verify log shape.

### Judge-Loop Transcript Review

- Clean smoke label: `smoke_judge_loop_transcript_20260429_runtime_fixed_1case`.
- Example case log: `experiments/evals/v5_forward_eval/smoke_judge_loop_transcript_20260429_runtime_fixed_1case/test/web_scrape_hq/afatinib_egfr_ic50_salts/run.log`.
- The smoke produced `run.log` with 349 lines and `run.events.jsonl` with `case_start`, `iteration_done`, and `case_complete`.
- The runtime judge accepted the result (`judge_decision=True`, `judge_score=1.0`), while the deterministic scorer marked it partial (`score=0.85`) because `compound_chembl_id` contained numeric molregno values instead of expected CHEMBL IDs.

## Next GEPA Experiment Plan - Full Diverse-1010 Judge Loop (2026-04-29)

- [ ] Confirm the experimental protocol before implementation: optimize on diverse-1010 train only, select on diverse-1010 val, touch diverse-1010 test only once for final accuracy estimate.
- [ ] Patch or add a GEPA runner that evaluates candidates through the full J-Judge loop, not the one-shot PF_UP/PF_SQL/PF_RES path.
- [ ] Ensure candidate fitness uses deterministic result agreement after the judge loop terminates; judge score is diagnostic/loop-control, not the benchmark authority.
- [ ] Decide whether GEPA may mutate `pf.judge`; if yes, add a guardrail so candidate selection cannot be driven by the candidate's self-judge score.
- [ ] Run a tiny smoke on a small train/val slice to verify artifacts include `run.log`, `run.events.jsonl`, `judge_loop_iterations.json`, and deterministic scores.
- [ ] Run baseline v5.10 on full diverse-1010 val using the same judge-loop evaluator.
- [ ] Run GEPA on full diverse-1010 train with diverse-1010 val selection.
- [ ] Run best GEPA candidate on full diverse-1010 val and compare directly against the v5.10 val baseline.
- [ ] If best GEPA is better on val by a predeclared gate, promote it to the next prompt-pack version.
- [ ] Run the promoted candidate once on full diverse-1010 test and report that as the current best accuracy estimate.

### Protocol Notes

- Canonical split: `experiments/case_splits_v5.1010.json` with `train=742`, `val=130`, `test=138`.
- Prior long GEPA split was only `experiments/case_splits_v5.1010_gepa_probe.json` with `train=58`, `val=20`, `test=30`; its 30-case held-out result was a probe signal, not a final 1010 test estimate.
- Avoid optimizing on `test`; use `test` only after selecting/promoting by `val`.
- GEPA should use the full judge loop for candidate execution, but final fitness should remain deterministic ground-truth result agreement to avoid optimizing the judge into accepting bad results.

## Train-Only Sub-110 Judge GEPA (2026-04-29)

- [x] Create train-only sub-110 split from canonical diverse-1010 train cases.
- [x] Split internal GEPA partitions as train=55, val=25, test=30, with canonical diverse-1010 val/test untouched.
- [x] Patch `experiments/gepa_optimize_prompt_pack_v5.py` to support judge-loop candidate scoring.
- [x] Add `--mutable-fields pf.judge` support so UP/SQL/system prompts remain fixed at v5.10 for this experiment.
- [x] Add nested v5 prompt-pack to runtime prompt-pack adapter for `ChEMBLLLMQuery`.
- [x] Add run-level `run.log` plus per-case `run.log`/`run.events.jsonl` transcript artifacts in GEPA judge-loop mode.
- [x] Smoke-test judge-loop GEPA path on 1/1/1 cases.
- [x] Launch substantive sub-110 judge-prompt GEPA run.

### Sub-110 Judge GEPA Review

- Split: `experiments/case_splits_v5.1010_trainonly_gepa_judge_sub110.json`.
- Split counts: train=55, val=25, test=30; all cases are drawn from canonical `experiments/case_splits_v5.1010.json` train.
- Smoke run: `experiments/evals/v5_forward_eval/gepa_judge_sub110_smoke_20260429_transcript2`.
- Smoke finding: baseline v5.10 judge prompt repeatedly produced JSON wrapped as fenced JSON or otherwise malformed for the parser, so correct-looking SQL can be rejected and the loop can exhaust. This is a useful direct target for `pf.judge` GEPA.
- Active run screen: `gepa_judge_sub110_v510_zai47_8081fb_20260429_181649_r120`.
- Active run dir: `experiments/evals/v5_forward_eval/gepa_judge_sub110_v510_zai47_8081fb_20260429_181649`.
- Active run log: `logs/gepa_judge_sub110_v510_zai47_8081fb_20260429_181649.log`.
- Active run config: `--metric-mode judge-loop --mutable-fields pf.judge --judge-loop-max-iterations 5 --max-metric-calls 120`, primary `zai-anthropic/glm-4.7`, fallback `llamacpp@http://127.0.0.1:8081`.

### Next Judge GEPA Run Parameter Adjustment (2026-04-29)

- [x] Set next judge-loop GEPA max iterations to `10`.
- [x] Set next judge-loop GEPA per-call timeout to `600s` instead of `1200s`.
- [x] Update saved relaunch script for the active sub-110 run label with `--judge-loop-max-iterations 10 --timeout 600`.

## Local-Only Sub-110 Judge GEPA Rerun (2026-04-30)

- [x] Reuse split `experiments/case_splits_v5.1010_trainonly_gepa_judge_sub110.json` and seed `experiments/prompt_pack_v5.10.yaml`.
- [x] Force task SQL/judge provider to local llama.cpp on `http://127.0.0.1:8081` with `nemotron-cascade-2-30b-a3b`.
- [x] Force GEPA reflection/proposal LM to the same local endpoint via LiteLLM OpenAI-compatible routing.
- [ ] Let the local-only run finish and compare against the GLM-4.7 run: `14/30`, pass rate `0.466667`, mean score `0.865799`.
- Relaunched corrected local-only run: screen `gepa_local_20260430_042954`, run dir `experiments/evals/v5_forward_eval/gepa_jsub110_v510_localonly_nemotron_8081_20260430_042954`, log `logs/gepa_jsub110_v510_localonly_nemotron_8081_20260430_042954.log`.

## GEPA Family Frontier And Exhausted-Best Return (2026-04-30)

- [x] Add family-aware objective scores to GEPA side-info: `deterministic` plus `family::<family>`.
- [x] Keep the existing GEPA `frontier_type=hybrid`, so the Pareto frontier now has per-case, deterministic-objective, and family-objective entries.
- [x] Change judge-loop exhaustion behavior to return the highest judge-score result table seen across iterations instead of returning no result.
- [x] Preserve the selected best SQL/UP/judge metadata in `latest_*` fields and mark `judge_loop_exhausted`/`returned_iteration` in GEPA/eval artifacts.

## GEPA Case Context Before System Prompt (2026-04-30)

- [x] Add optional runtime `case_context` metadata to `ChEMBLLLMQuery`.
- [x] Emit `CASE_CONTEXT` before `SP_SHA256` and `SP_FULL` so `less` readers see case progress before the full system prompt block.
- [x] Wire GEPA judge-loop calls to include ordinal/total, split, corpus, case id, family, manifest path, case artifact directory, candidate hash, and metric mode.
- [x] Syntax-check the patched runtime and GEPA runner.

## Harness Case Context And Judge Text Logging (2026-04-30)

- [x] Add pre-SP case context to non-GEPA judge-loop evaluation harness.
- [x] Check whether standalone one-shot forward harness needs equivalent case-progress context before prompt output.
- [x] Inspect runtime judge parsing/logging to verify written judge rationales are retained.
- [x] Log judge written evaluation/improvement text in runtime INFO logs for YES and NO decisions.
- [x] Syntax-check changed files and record results.
