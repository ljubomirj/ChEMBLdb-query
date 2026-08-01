# Model-Serving Minefield — Hipfire Endpoint Audit Report

**Date:** 2026-07-30  
**Endpoint tested:** `http://127.0.0.1:8081/v1` (Hipfire feature daemon, `feature/gbnf-and-reasoning-budget`)  
**Model:** `qwen3.6:27b.mq4`  
**Tool used:** [Blackwellboy/model-serving-minefield](https://github.com/Blackwellboy/model-serving-minefield) doctor (`minefield_doctor.py`), plus targeted manual probes

## What the minefield is

A community registry of **108 serving-path traps** that produce confidently wrong measurements: chat templates, tool parsers, reasoning fields, quantization kernel paths, container toolchains, memory allocation, eval harnesses, versioning. The common shape: the request looks correct, the response looks correct, and the number is still wrong, because something between the two was never inspected.

The included **doctor** (`minefield_doctor.py`) is a bounded, read-only preflight that implements checks for 19 of the 108 traps — weighted toward reasoning fields, templates, thinking control, tool parsing, and token ceilings. A clean run from it is a statement about the traps it touched, never a bill of health.

## What was run

1. `minefield_doctor.py --base-url http://127.0.0.1:8081/v1` — 13 generation requests, ~87s, against the live Hipfire endpoint
2. Manual thinking-toggle probes (default vs `enable_thinking=false` vs string `"false"` vs `reasoning_effort=none`) on easy and hard tasks
3. `/props` probe (404 — this fork exposes no `/props`)
4. `hipfire serve --help` — flag surface inspection
5. Review of the 6 `case_error.json` artifacts from the completed 1010-case run

## Findings

### PROBLEMS (2, both reproduced live)

**1. Trap 77 — the request surface is unvalidated.**
An invented top-level field (`__minefield_unvalidated_field_probe__`) was accepted with HTTP 200, identical to the baseline without it. Consequence: **nothing you send to this lane is confirmed by its status code.** A parameter you misspell, or one the server does not implement, is silently dropped and the lane runs on its defaults.

Direct impact on this setup: `chat_template_kwargs.enable_thinking=false` does **not** suppress thinking. On a reasoning-heavy task the model reasoned anyway under `enable_thinking=false`, under integer `0`, and under `enable_thinking="false"` (string — trap 57 territory). `reasoning_effort=none` errored. The thinking gate on this server is **server-side only** (`thinking on` + `max_think_tokens` in config); client kwargs are decorative.

> Not a problem for the Text2SQL pipeline — thinking is *desired* there and the run config sets it server-side. But any client that believes `enable_thinking=false` disables thinking on this endpoint is measuring a thinking lane.

**2. Trap 12 — empty content at the token ceiling.**
Hard task at `max_tokens=512`: HTTP 200, `finish_reason=length`, **empty content**, 1519 chars of reasoning consumed. The reasoning budget ate the whole generation budget and the server returned success with nothing usable.

Impact on this setup: the pipeline calls use `max_tokens=10240` per stage (UP/SQL/judge), far above the 512 probe, so the 1010 run was not affected. But the behavior is real: **any harness that scores empty content as a model failure is measuring its own budget.** The minefield's own trap-22 note: a 27B converted 0/3 at an 8192 thinking budget and only 2/3 at 16384 — the conversion floor is a distribution, not a threshold.

### CHECKED AND CLEAN (3)

- **Trap 01:** reasoning exposed under `reasoning_content` (the field name the runtime reads)
- **Trap 02:** no orphaned `</think>` at the start of probe responses
- **Trap 23:** streamed answers arrive in content deltas, not stranded in the reasoning channel

### INCONCLUSIVE / COULD NOT CHECK (the important gaps)

- **Tool calling (trap 19 / 26 / 78):** both tool probes returned HTTP 200 but **unusable** content. `hipfire serve --help` shows **no `--jinja` flag, no `--tool-call-parser`**, and no tool-related surface at all. This is a llama.cpp fork whose serve line carries only `--kv-mode`, `--grammar-file`, `--idle-timeout`. **The native tool-call path is either absent or unproven** — which is exactly the shape of trap 19 (`--jinja` missing turns structured tool calls into prose). The doctor's `tool_choice` gate check was INCONCLUSIVE for the same reason.
- **Template render inspection (trap 04/20/25):** no `/apply-template`, no `/props`, no tokenize-with-tokens — this fork exposes no render forensics path. History-reasoning stripping cannot be checked against the live server.
- **Thinking kwarg map (trap 03/07/29):** cannot be settled because the doctor cannot identify the stack and client kwargs demonstrably don't gate thinking.
- **Quant / config checks (trap 10/17/21):** need `--hf-repo`; not run.

### The 1010-run error artifacts are NOT serving bugs

The 6 `case_error.json` artifacts from the completed run break down as:

| Error | Count | Cause class |
|---|---|---|
| `Query returned no result` | 3 | SQL ran, zero rows (data/join semantics, not serving) |
| `column 'molecule_chembl_id' is duplicate` | 1 | Duplicate output columns → Polars materialization failure (known v5 issue) |
| `could not parse ... as dtype i64 at column 'pubmed_id_or_doi'` | 2 | Mixed PMID/DOI column typing (known normalization issue) |

None are empty-content/token-ceiling events. The LLM produced content in all six; the failures are downstream data-shape issues in the benchmark/harness.

## What needs changing

### High priority

1. **Never treat client kwargs as controlling on this endpoint.** If a future run needs thinking off, it must be a **server-side** config change (`thinking off` / `max_think_tokens`), not `chat_template_kwargs`. Document this on the serving contract. (Trap 77/29 workaround; no server code change needed unless client-side control is required.)

2. **Bucket cap-hits before scoring.** If any harness stage ever runs this endpoint with a tight `max_tokens`, `finish_reason=length` + empty content must be treated as a budget artifact (retry with more budget), never as a model failure. (Trap 12.)

### Medium priority

3. **Decide whether tool calling is a requirement.** If agents (e.g. OMP/Hermes against this endpoint) need structured tool calls, the fork needs a `--jinja`-equivalent + tool-call parser — currently absent from the serve surface. Until then, any "model cannot tool-call" conclusion about Qwen3.6 on this stack is a **serving-surface conclusion, not a model conclusion** (trap 19). For the Text2SQL pipeline this is moot: it uses GBNF grammar for JSON, not function calling.

4. **Template compatibility check (trap 24).** Qwen3.5/3.6 official templates contain Python-only Jinja constructs (`|items`); C++ engines silently misrender. The minefield found current llama.cpp largely past this, but this is a **fork** on a feature branch — verify the GGUF-embedded template renders correctly by diffing a rendered prompt against a reference Python-Jinja2 render (`checks/preflight_template.py`). Record the template hash + engine next to every published number.

### Low priority / informational

5. **No `/props` = fewer diagnostics.** The fork exposes no `/props` or `/apply-template`. Context reporting (trap 87) and render forensics are unavailable; keep the serve-line manifest (`manifest.txt` in the artifact tree) as the source of truth for served config.

6. **The run's own errors stay in the harness.** The duplicate-column and PMID/DOI-type failures are known v5 harness issues (LEARNINGS 2026-03-21, 2026-03-16); fixing them is a benchmark/data fix, not a server fix.

## Bottom line

- The server **passed** the 3 checks the doctor could execute cleanly (reasoning field, think-tag hygiene, streaming).
- It **failed** 2: unvalidated request surface (trap 77) and empty-content-at-ceiling (trap 12). Both are config/harness-shaped, not model-shaped, and neither affected the completed 1010 run (which used 10K-token ceilings and server-side thinking control).
- The **real open question is tool calling**: the serve surface has no tool-parser path, so structured tool use on this endpoint is unsupported/unproven.
- No urgent server defect requires fixing before the next Text2SQL run. The concrete changes are: document the server-side thinking gate, bucket cap-hits in any tight-budget harness, and (if agents need tools) add a tool-call surface to the fork.
