# v5 Design

## Current status — April 2026

This document started as a forward-looking design note. It is now partly design, partly status record.

Current live state:

- the active corpus is the diversified **`v5.1010`** dataset, not the old undiversified `1000`
- the full 1010-case judge-loop baseline has completed at:
  - `runs/v5_1010_full_judge_loop_20260409_101200/`
- current full-run summary:
  - `1010` cases
  - `350` exact passes
  - pass rate `0.346535`
  - mean score `0.787994`
- the ordered case list now lives in that `report.json` with stable `ordinal` fields `1..1010`

The design intent below is still the right direction, but it is no longer hypothetical: the repo already has a working v5 runtime/evaluation surface around

- `src/db_llm_runtime_v5.py`
- `src/db_llm_v5/`
- `scripts/evaluate_v5_forward_judge_loop.py`

## Why v5 still matters

The main idea is not “yet another prompt pack”.

The main idea is to make the repo support **both**:

- forward execution (`UQ -> UP -> SQL -> RES -> J`)
- backward reconstruction / data synthesis (`SQL -> UP_exec -> UQ_surface`)

That matters for the next phase of the project because we need:

- better benchmark diagnostics
- realistic synthetic or repaired cases
- forward/backward consistency checks
- prompt optimization over explicit artifacts rather than hidden ad-hoc text blobs

## Purpose

`v5` should separate four concerns that are currently too entangled in `v4`:

1. forward query generation
2. backward data curation
3. benchmark evaluation
4. prompt optimization

The goal is not another prompt tweak. The goal is a cleaner system with explicit artifacts and explicit transformations between them.

## Naming

Use `case` as the top-level unit.

Why `case`
- It works for benchmark items, curated items, generated items, and failed items.
- It does not imply randomness the way `sample` does.
- It is more concrete than `example`.

Recommended terms
- `case`: one benchmark/data item
- `corpus`: a collection of cases
- `split`: a train/val/test partition of a corpus
- `artifact`: any file produced or stored for a case
- `prompt pack`: the set of prompt templates used by a pipeline

So the current `1000` items should be described as:
- a `1000-case corpus`
- or the `v4.7 corpus of 1000 cases`

## Artifact Model

Each case should have explicit artifacts instead of overloading `uq.txt` to do too much.

### Core forward artifacts

- `uq_surface.txt`
  - realistic human-facing wording
- `up_exec.txt`
  - execution-oriented semantic plan
- `sql_gold.sql`
  - authoritative executable SQL
- `res_gold.csv`
  - authoritative result table

### Optional benchmark artifacts

- `uq_benchmark_spec.txt`
  - explicit benchmark semantics when realism alone is insufficient
- `res_gold_presentation.csv`
  - optional human-facing presentation variant of the result
- `sql_alt_*.sql`
  - optional alternative equivalent SQL forms

### Metadata

- `metadata.json`
  - provenance
  - family
  - realism level
  - ambiguity level
  - expected output schema
  - sort keys
  - case tags
  - whether multiple SQLs are acceptable

## Forward Pipeline

Adopt the user terminology.

- `(ctx) UQ + PF_UP -> UP`
- `(ctx) UP + PF_SQL -> SQL`
- `SQL -> RES`
- `(ctx) RES + PF_J -> J`

Definitions
- `UQ`: user question, surface form
- `UP`: execution-oriented user prompt, not SQL, not a copy of UQ
- `SQL`: executable SQLite query
- `RES`: result table
- `J`: iterative diagnostic only

Important
- `J` is not the benchmark authority.
- `J` is only for deciding whether to continue from iteration `N` to `N+1`.
- Benchmarking should remain deterministic and separate.

## Backward Pipeline

The backward path should not jump directly from SQL to final surface UQ in one step.

Use layered reconstruction:

- `(ctx) SQL + PB_SQL -> UP_exec`
- `(ctx) UP_exec + PB_UP -> UQ_surface`

Optional extension:

- `(ctx) SQL + RES + PB_RES -> intent sketch`

Then:

- `intent sketch -> UP_exec`
- `UP_exec -> UQ_surface`

This is more robust than a single `SQL -> UQ` jump because it separates:
- execution semantics
- human phrasing

## Prompt-Pack Schema

`v5` prompt packs should explicitly separate forward and backward prompts.

Suggested YAML shape:

```yaml
version: v5.0

system:
  about_block: ...
  schema_block: ...
  hint_block: ...
  examples_block: ...

pf:
  up: |
    ...
  sql: |
    ...
  judge: |
    ...

pb:
  sql_to_up: |
    ...
  up_to_uq: |
    ...
  res_sql_to_intent: |
    ...

scoring:
  judge_threshold: 0.9
  uq_up_echo_penalty_threshold: 0.95
  uq_up_echo_penalty_weight: 0.15
```

That gives a single coherent prompt pack while still exposing the forward/backward distinction.

## Core Library

Do not build `v5` as two unrelated monoliths.

Build one shared core with two thin CLIs on top.

### Shared core responsibilities

- prompt pack loading
- context assembly
- artifact loading and writing
- provider dispatch
- fallback handling
- deterministic scoring
- case schema validation
- audit utilities

### Forward CLI

- `src/db_llm_query_v5.py`
- purpose:
  - live querying
  - iterative refinement
  - benchmark execution

### Backward CLI

- `src/db_llm_back_v5.py`
- purpose:
  - SQL -> UP reconstruction
  - UP -> UQ reconstruction
  - dataset curation
  - synthetic case generation

This avoids duplicating provider logic, prompt loading, and artifact handling.

## What UP Should Be

`UP` should be a compact execution plan, not one of these:
- not a copy of `UQ`
- not lightly edited `UQ`
- not raw SQL
- not benchmark-spec leakage

`UP` should explicitly capture:
- entities and relations
- required output schema
- key filters
- ranking/sorting
- row-cap semantics
- deduplication semantics when relevant

A good `UP` should preserve intent while compressing surface phrasing into execution-relevant structure.

## Evaluation Model

### Deterministic benchmark evaluation

This remains the authority for benchmark quality.

Measure at least:
- exact pass / partial / fail
- schema match
- row match
- value match
- result materialization success

### LLM judge evaluation

This is for iterative control only.

Use `J` to answer:
- should we stop now?
- what likely went wrong?
- what should the next iteration improve?

Do not use `J` as the final benchmark truth.

### Intermediate artifact evaluation

`v5` should also score intermediate artifacts directly.

For `UQ -> UP`
- semantic preservation
- low UQ echo
- no SQL leakage
- output-schema clarity

For `UP -> SQL`
- executability
- alias correctness
- schema correctness
- join-path correctness

For `SQL -> RES`
- deterministic correctness

For backward artifacts
- `SQL -> UP_exec` fidelity
- `UP_exec -> UQ_surface` realism

## Data Quality Priorities

The current corpus is strong in size but still unbalanced in family mix.

Current risk
- `target_pchembl` dominates the corpus
- this can distort prompt optimization and benchmark conclusions

Quality priorities
1. rebalance families
2. keep realistic `uq_surface`
3. keep benchmark-spec separate
4. label realism explicitly
5. label ambiguity explicitly

Suggested metadata fields

```json
{
  "case_id": "...",
  "family": "target_pchembl",
  "origin": "templated_from_sql",
  "realism_level": "realistic_surface",
  "ambiguity_level": "unambiguous",
  "requires_schema_alias_fidelity": true,
  "allows_multiple_sql_forms": true,
  "gold_sort_keys": ["molecule_chembl_id", "assay_chembl_id"]
}
```

## DSPy Fit

DSPy is useful here, but only for part of the problem.

Where DSPy fits well
- optimizing prompt text artifacts
- separating signatures for:
  - `PF_UP`
  - `PF_SQL`
  - `PF_J`
  - `PB_SQL`
  - `PB_UP`
- running targeted search over prompt fields

Where DSPy does not solve the core architecture
- case schema design
- benchmark design
- deterministic scoring
- artifact provenance
- transport/provider fallback
- dataset curation workflow

Conclusion
- use DSPy inside `v5`
- do not let DSPy define `v5`

In practice
- DSPy should optimize prompt modules
- the `v5` core should define the artifact and evaluation framework

## SQL Intermediate Qualities

The SQL-quality idea from the walking notes is valid.

Do not treat SQL quality as one scalar only.

Track intermediate descriptors such as:
- SQL length
- number of `JOIN`s
- number of `WITH` clauses
- max nesting depth
- presence of aggregation
- presence of `DISTINCT`
- number of projected columns
- number of sort keys
- execution time
- result row count
- query plan complexity

These descriptors are useful in two ways.

### 1. Analysis

They help explain failure clusters.

Examples
- alias failures may correlate with wider projection width
- wrong deduplication may correlate with `DISTINCT`
- brittle prompts may correlate with more join-heavy cases

### 2. Quality-diversity search

These descriptors could define behavior-space axes for:
- MAP-Elites
- quality-diversity search
- Pareto frontier analysis

Example behavior map
- axis 1: join count
- axis 2: CTE count
- quality: final benchmark score

That would let you keep the best prompt or best reconstructed artifact for each structural region instead of only searching for one global winner.

This is worth doing, but only after `v5` artifact boundaries are explicit.

## Migration Plan

### Phase 1

Define the `v5` schemas without changing runtime behavior.

Deliverables
- `v5` prompt-pack schema
- `v5` case schema
- migration scripts from `v4` case artifacts

### Phase 2

Build the shared core library.

Deliverables
- prompt-pack loader
- case loader
- artifact writer
- provider abstraction
- deterministic scorer

### Phase 3

Build the two CLIs.

Deliverables
- `db_llm_query_v5.py`
- `db_llm_back_v5.py`

### Phase 4

Add intermediate scoring and audits.

Deliverables
- `UQ -> UP` echo audit
- `SQL structural descriptor` extraction
- backward-fidelity audit

### Phase 5

Run optimization again.

Targets
- `PF_UP` first
- `PF_SQL` second
- backward prompts after that

## Immediate Recommendation

Do not start with a full migration.

Start with these concrete steps:
1. define `v5` case schema and prompt-pack schema
2. add backward prompt placeholders to a new `v5` pack
3. add SQL structural descriptors to current evaluation reports
4. keep `v4.11` as the live baseline until `v5` scaffolding is stable
