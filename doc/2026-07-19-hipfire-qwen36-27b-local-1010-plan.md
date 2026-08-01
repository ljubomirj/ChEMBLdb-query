# Qwen3.6-27B local-only Text2SQL benchmark plan

Date: 2026-07-19  
Host: gigul2, RX 7900 XTX / gfx1100, 24 GB VRAM

## Objective

Run the ChEMBL v5.1010 benchmark entirely through the local Hipfire
Qwen3.6-27B endpoint. The same model and endpoint must perform all three LLM
roles used by the earlier DeepSeek-V4-Flash run:

1. UP/prompt writer
2. SQL generator
3. Judge

This is an indicative local-vs-cloud experiment, not a clean engine comparison:
the local model, quantization, grammar, sampling path, and latency differ from
the previous DeepSeek provider.

## Serving contract

- Hipfire feature branch `feature/gbnf-and-reasoning-budget`, source SHA
  recorded in the run manifest.
- Qwen3.6-27B MQ4, `asym2` KV, `max_seq=262144`.
- Ordinary AR: DFlash, MTP, n-gram, CASK, and speculation off.
- Thinking enabled with `max_think_tokens=4096` and
  `max_total_think_tokens=4096`.
- `max_tokens=10240` at the server and for UP, SQL, and judge calls.
- Reasoning-budget exhaustion message enabled.
- Server-side stage-agnostic GBNF: exactly one closed `<think>` block followed
  by a complete JSON object. All three role prompts request JSON; stage keys
  remain validated by the Python parser.

The previously running server used the LiveCodeBench fenced-Python grammar;
the runner replaces it with the Text2SQL grammar for this experiment and
restores the normal LiveCodeBench service on exit.

## Gates and execution

1. Build the feature daemon and retain its SHA-256 beside the results.
2. Run one held-out case through all three local roles. Inspect raw UP, SQL,
   SQLite rows, judge JSON, token-budget behavior, and server logs.
3. If the gate completes without server/grammar/parser failure, run all 1,010
   cases with `--max-iterations 10` and `--skip-existing`.
4. Monitor stage transitions, case completion, retries, context-full events,
   malformed outputs, and wall time. If interrupted, restart the same artifact
   directory with `--skip-existing`; do not mix changed serving contracts into
   the result.
5. Report pass rate, mean/median score, deterministic score, role latency,
   retry/failure counts, total wall time, and the exact configuration/artifacts.

## Initial gate result

The one-case gate completed UP, SQL, SQLite, and judge successfully. The local
judge accepted it with score 1.0; the deterministic case score was 0.630769,
so it establishes pipeline operability rather than high accuracy. UP took about
4m47s, SQL about 3m, and judge about 1m11s with the 100–112K-character prompt.

## Run status

The full run was launched with the durable runner
`/opt/ljubomir/LJ-amdgpu-7900xtx/scripts/run_hipfire_qwen36_27b_text2sql_1010.sh`
under:

```text
artifacts/7900xtx-rocm-speed/hipfire-qwen36-27b-text2sql-1010-20260719_231825/
```

The first pass completed cases 1, 2, and 4. Case 3 exhausted all ten
iterations because the permissive `answer ::= .+` grammar allowed EOS after a
single `{`, producing truncated UP JSON. The daemon and endpoint were healthy;
this was a grammar-contract failure. The run was stopped with those artifacts
preserved.

The grammar was then changed to a role-agnostic but balanced JSON-object
grammar (`answer ::= object`, with recursive JSON strings/arrays/numbers). The
same artifact was resumed with `--skip-existing`. Case 3 then completed on its
first iteration: UP, SQL, and judge all parsed; the judge returned YES with
score 1.0, and the deterministic output was saved. Constrained decoding is
slower (UP about four minutes for a ~100K-character prompt), but removes the
truncation failure. The resumed run is active and has produced 14 result
artifacts as of the latest watchdog check.

An hourly cron watchdog is installed at minute 7:

```text
/opt/ljubomir/LJ-amdgpu-7900xtx/scripts/watch_hipfire_qwen36_27b_text2sql_1010.sh
```

It uses an artifact-local lock, checks runner ownership, HTTP health, and
evaluator log age, then resumes the same artifact with `--skip-existing` only
when the job is absent or genuinely stale. On completion it invokes
`report_hipfire_qwen36_27b_text2sql_1010.py`, writing `episode-report.md` beside
the raw logs.
