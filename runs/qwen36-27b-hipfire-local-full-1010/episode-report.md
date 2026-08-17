# Qwen3.6-27B local-only ChEMBL v5.1010 episode report

**Artifact:** `/opt/ljubomir/LJ-amdgpu-7900xtx/artifacts/7900xtx-rocm-speed/hipfire-qwen36-27b-text2sql-1010-20260719_231825`  
**Generated:** `2026-07-29T21:53:36+01:00`  
**Expected cases:** `1010`  
**Completed result artifacts:** `1006`  
**Case-error artifacts retained:** `6`  
**Deterministic scores available:** `1006`  

## Configuration

- Feature daemon: `feature/gbnf-and-reasoning-budget` (SHA and daemon hash in `manifest.txt`).
- Qwen3.6-27B MQ4, `asym2`, `max_seq=262144`, `max_tokens=10240`.
- Thinking on; `max_think_tokens=max_total_think_tokens=4096` with the reasoning-budget exhaustion message.
- MTP, DFlash, speculation, n-gram, and CASK off.
- One local Hipfire endpoint for UP writer, SQL writer, and judge.
- Final grammar SHA-256: `a798162e306bfed9139ce42f4b03cda8cbeb308acd341f382f3326a5015c8acd`.

## Results so far

- Judge winner lines: `1121`; accepted judge decisions: `3723`.
- Deterministic status counts: `{"partial": 685, "pass": 321}`.
- Deterministic mean: `0.7782`; median: `0.8000`; >=0.9: `398/1006`.
- Generation stages observed: `1121`; median wall time `120.7s`.
- Query executions observed: `1063`; median wall time `5.53s`.

## Episode history and failure analysis

1. A one-case preflight completed all three local roles and a valid judge response, proving the serving contract before the full run.
2. The first full pass used a shared thinking-block grammar with `answer ::= .+`. That grammar accepted EOS after the first visible character. Case 3 repeatedly returned truncated UP JSON beginning with `{\"`, exhausted ten iterations, and produced no result. The daemon, GPU, and HTTP health endpoint remained healthy; this was a grammar-contract failure, not a crash.
3. The runner stopped safely, preserving the completed cases and logs. The grammar was changed to a role-agnostic balanced JSON-object grammar. Since all three prompts request JSON, this enforces closure without hard-coding UP/SQL/judge keys.
4. The same artifact was resumed with `--skip-existing`. Case 3 completed on its first repaired iteration with valid UP, SQL, judge JSON, judge score 1.0, and a deterministic result. The stricter grammar costs latency, especially on the large schema prompt, but prevents the observed truncation.
5. Malformed-output log events retained: `6`; exhausted-iteration events retained: `3`. See `evaluator.log`, per-case `run.log`, and `case_error.json` files for exact traces.

## Prevention for the next run

- Use a balanced JSON grammar whenever every stage's public contract is JSON; never use an unconstrained `.+` answer tail when EOS validity matters.
- Run the one-case gate before spending the full quota, and keep it as a separate artifact.
- Launch the resumable runner under `setsid`, keep `--skip-existing`, and retain the exact daemon/model/grammar hashes.
- Keep an hourly watchdog active for long GPU jobs; it must restart only after confirming the runner is absent or stale, avoiding duplicate servers.

## Raw evidence

- `manifest.txt`, `health.json`, `models.json` — serving contract and hashes.
- `launcher*.log`, `server.log`, `evaluator.log` — complete episode timeline.
- `evals/hipfire_qwen36_27b_text2sql_1010/` — per-case outputs, scores, errors, and event logs.
