# Qwen3.6-27B local Text2SQL run — paused status

Date paused: 2026-07-20 09:14 BST  
Host: gigul2 / RX 7900 XTX  
Artifact (original location, now a symlink):
`/opt/ljubomir/LJ-amdgpu-7900xtx/artifacts/7900xtx-rocm-speed/hipfire-qwen36-27b-text2sql-1010-20260719_231825/` →
`/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/qwen36-27b-hipfire-local-full-1010/`

## Restart later

The evaluator, feature daemon, normal 8081 service, and hourly watchdog are
currently stopped. The cron watchdog was deliberately removed so the GPU stays
free. When the GPU is available again:

```bash
cd /opt/ljubomir/LJ-amdgpu-7900xtx
OUT_DIR=/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/qwen36-27b-hipfire-local-full-1010
setsid env OUT_DIR="$OUT_DIR" MAX_ITERATIONS=10 CELL_TIMEOUT_SECONDS=0 TEXT2SQL_LIMIT= \
  bash scripts/run_hipfire_qwen36_27b_text2sql_1010.sh \
  >"$OUT_DIR/launcher-resume.log" 2>&1 < /dev/null &
```

The runner always passes `--skip-existing`, so it resumes this artifact rather
than restarting at case 1. If hourly babysitting is wanted again, re-add this
line to the user's crontab:

```cron
7 * * * * /opt/ljubomir/LJ-amdgpu-7900xtx/scripts/watch_hipfire_qwen36_27b_text2sql_1010.sh
```

## What was achieved

The canonical manifest is 1,010 cases: 742 train, 130 validation, and 138
test. At pause, 76 cases had `pf_res.output.json` result artifacts, or 7.5% of
the full set. Two `case_error.json` files remain as provenance: one is the
original permissive-grammar truncation case, and one reached a valid judge
verdict but failed to produce a result artifact. The server and evaluator were
healthy when interrupted; this was an intentional pause, not a crash.

The first full-pass grammar failure was repaired. The old `answer ::= .+` rule
allowed EOS after a lone `{`, repeatedly producing truncated UP JSON. The
balanced role-agnostic JSON grammar fixed the case on its first resumed
iteration. All three roles—UP writer, SQL writer, and judge—ran locally through
Qwen3.6-27B with 262K context, asym2 KV, thinking capped at 4,096 tokens, and
MTP/DFlash/speculation disabled.

## Remaining work

934 cases remained. Watchdog history measured approximately 7.8 cases/hour:

- Estimated remaining time: approximately 120 hours, about 5 days.
- This is only a planning estimate; large result sets and judge calls vary.

## Comparison with the earlier DeepSeek-V4-Flash run

The prior cloud run used DeepSeek-V4-Flash through OpenCode Go for all three
roles. Its successful test-split evidence was much further along in accuracy:

- Initial report: 71/138 completed, 98.6% pass rate, mean score 0.985.
- Follow-up accounting: 109/138 completed, 100% above the 0.9 threshold, mean
  score 0.992; 29 cases were blocked by oversized result/judge payloads.
- The attempted full 1,010-case cloud run was stopped after very high token
  usage: roughly 4% of quota produced only a handful of completed cases because
  the full schema was repeatedly sent to the provider and OpenCode Go imposed a
  much lower effective context limit than direct DeepSeek.

The local run is not yet comparable on accuracy: it has only 76/1,010 results
and no final aggregate. It is also a different model and serving path, so the
cloud pass rate is a reference point, not a controlled model comparison. The
local advantage is zero per-token API cost and a reproducible, resumable local
artifact; the disadvantage is throughput—roughly five days for the full set at
the observed rate.

## Evidence

- `evaluator.log` — complete evaluator timeline.
- `server.log` — Hipfire feature-daemon serving log.
- `watchdog.log` — hourly progress history before the intentional pause.
- `manifest.txt` — model, daemon, grammar, source, and configuration hashes.
- `episode-report.md` — final episode report (auto-generated when the run completed).

## Second pause — 2026-07-24 15:45 BST

The run was intentionally paused again to reduce room noise and fan activity.
At interruption it had **249 completed results (24.7%)** and had just begun
ordinal case **250/1010**. The same two historical case-error artifacts remain;
no new error was introduced by this pause. The evaluator, feature daemon,
restored Hipfire service, and two-hour watchdog cron entry were stopped. Port
8081 is free and ROCm reports 0% VRAM allocated.

Resume using the command above, then re-add the watchdog at the two-hour
schedule if desired:

```cron
7 */2 * * * /opt/ljubomir/LJ-amdgpu-7900xtx/scripts/watch_hipfire_qwen36_27b_text2sql_1010.sh
```

## Resume — 2026-07-24 18:15 BST

The run was resumed with the same configuration. The evaluator restarted at ordinal
case **250/1010** (the first unfinished case after 249 completed results). The
Hipfire grammar branch server is healthy on port 8081 with the balanced Text2SQL
grammar. The two-hour watchdog was re-enabled. Expected throughput ~7.8 cases/hour
for the remaining ~761 cases.

## Completion — 2026-07-29 18:58 BST

The run completed all **1,010 cases** with **0 incomplete**. Final metrics:

| Metric | Value |
|--------|-------|
| Mean deterministic score | 0.7782 |
| Median | 0.8000 |
| Full passes (score = 1.0) | 321 (31.8%) |
| 1-shot cases | 882 (87.3%) |
| Failures | 4 |

See `episode-report.md` in the artifact directory for the full breakdown.

**Artifact moved to:**
`/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/qwen36-27b-hipfire-local-full-1010/`

A symlink remains at the original location. The watchdog cron was disabled;
the Hipfire server was left running as a shared resource.

