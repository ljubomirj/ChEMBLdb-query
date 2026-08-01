# v5 Judge-Loop Algorithm

This document describes the iterative Text-to-SQL algorithm used by the
ChEMBLdb-query pipeline. The same algorithm runs in v3, v4, and v5; v5 adds
explicit artifact boundaries and a backward reconstruction path in addition to
the forward query path described here.

## Overview

Given a natural-language **user question (UQ)** about the ChEMBL database, the
pipeline generates an executable SQL query, runs it against the local SQLite
database, and uses an LLM judge to decide whether the result is good enough.
If not, the pipeline iterates — refining the prompt and regenerating SQL — until
the judge accepts or the iteration budget is exhausted.

## Components

| Component | Role | LLM call |
|-----------|------|----------|
| **SP** (System Prompt) | ChEMBL schema docs, table descriptions, sampled rows, prompt hints | None — built once from SQLite introspection |
| **UQ** (User Question) | The natural-language query provided by the user | None — read from manifest |
| **UP** (User Prompt) | Execution-oriented rewrite of UQ: entities, relations, filters, output schema | Yes — prompt-writer LLM |
| **SQL** | Executable SQLite query | Yes — SQL-writer LLM |
| **RES** (Result) | Table returned by running SQL against ChEMBL SQLite | None — local SQLite execution |
| **J** (Judge) | Qualitative evaluation: score [0,1], YES/NO decision, improvement advice | Yes — judge LLM |

Every case makes **3 LLM calls per iteration**: UP, SQL, and Judge. The
pipeline loops through these until the Judge says YES (or the maximum iteration
count is reached).

## Flow diagram

```
UQ (from manifest)
 │
 ▼
┌──────────────────────────────────────────────────────────────┐
│  Iteration n = 1, 2, ..., N  (N = max_iterations)           │
│                                                              │
│  1. UP_n  = LLM(SP, UQ, history)                            │
│     ─ rewrite UQ into an execution-oriented plan             │
│                                                              │
│  2. SQL_n = LLM(SP, UQ, UP_n, history)                      │
│     ─ generate executable SQLite query                       │
│                                                              │
│  3. RES_n = SQLite(SQL_n)                                    │
│     ─ run SQL locally, get result table                      │
│     ─ capture: query plan, row count, columns, sample rows   │
│                                                              │
│  4. J_n   = LLM(SP, UQ, UP_n, SQL_n, RES_n summary, history)│
│     ─ evaluate: score [0,1], YES/NO, improvement advice      │
│                                                              │
│  Decision:                                                   │
│    if J_n.decision == YES  → STOP, accept SQL_n + RES_n     │
│    if J_n.decision == NO   → append (UP_n, SQL_n, RES_n,    │
│                               J_n) to history, continue      │
│    if n == N               → STOP, accept best available     │
└──────────────────────────────────────────────────────────────┘
```

## History

Each iteration's outputs are appended to a growing history that is passed to
subsequent iterations. The history window is configurable (default: all prior
iterations). This gives the UP and SQL writers feedback from the judge's
earlier critiques.

## Judge acceptance policy

The judge returns a score in [0,1] and a YES/NO decision. The acceptance
policy is **asymmetric**:

- **YES + score ≥ 0.5** → accept (the judge believes the answer is usable)
- **NO + score ≤ 0.99** → accept anyway (the judge says no but the
  deterministic score is very high, so override)
- **NO + score > 0.99** → reject (rare; judge sees a serious problem despite
  a high deterministic score)

When the iteration budget is exhausted without a YES, the pipeline returns the
iteration with the highest deterministic score seen so far.

## Deterministic scoring

Separately from the LLM judge, a **deterministic scorer** compares the
generated SQL result against a gold-standard `res_gold.csv` file. This is the
authoritative benchmark metric — not the judge's score. The deterministic score
measures:

- Column name match (aliased columns mapped)
- Row count agreement
- Cell value match

A score of 1.0 means exact match. Partial scores reflect partial column/row
overlap.

## Prompt packs

All prompt templates are stored in YAML prompt packs
(`experiments/prompt_pack_v5.*.yaml`). Each pack contains:

- `system.*` — SP building blocks (schema docs, hints, examples)
- `pf.up` — the UP writer task template
- `pf.sql` — the SQL writer task template
- `pf.judge` — the judge evaluation template

The prompt pack is versioned and immutable during a run. GEPA (the prompt
optimizer) proposes new prompt packs; the best is promoted and used as the
seed for the next optimization round.

## Key parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--max-iterations` | 10 | Maximum UP→SQL→RES→J cycles per case |
| `--judge-loop-max-iterations` | 10 | Alias for above in judge-loop runner |
| `--timeout` | 600s | Per-LLM-call timeout |
| `--judge-max-tokens` | 1200 | Max output tokens for judge response |
| `--sql-max-tokens` | 4000 | Max output tokens for SQL generation |
| `--up-max-tokens` | 1200 | Max output tokens for UP generation |
| `--local-enable-thinking` | on | Enable `<think>` blocks for local models |

## Implementation

The algorithm is implemented across:

- **`src/db_llm_runtime_v5.py`** — `ChEMBLLLMQuery` class: the core loop,
  provider dispatch, parsing, history management, fallback logic
- **`scripts/evaluate_v5_forward_judge_loop.py`** — the benchmark runner:
  iterates over a split of cases, calls `ChEMBLLLMQuery` per case, persists
  per-case artifacts, and generates the aggregate `report.json`
- **`src/db_llm_v5/`** — shared core: provider adapter, prompt pack loading,
  manifest I/O, deterministic scoring

## Related documents

- `doc/v5_design.md` — full v5 architecture (forward + backward paths)
- `doc/2026-07-19-hipfire-qwen36-27b-local-1010-plan.md` — the Hipfire run plan
- `doc/2026-07-29-hipfire-qwen36-27b-1010-run-report.md` — Hipfire run results
