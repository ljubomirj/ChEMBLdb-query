---
name: db-llm-query-chembl
description: Run and iterate ChEMBL natural-language queries via `src/db_llm_query.py`, including outer-loop refinement until results look correct. Use when asked to run repeated `db_llm_query` loops, adjust prompts, inspect outputs/logs, or orchestrate ChEMBL LLM query runs.
license: Unknown
metadata:
  skill-author: K-Dense Inc.
---

# DB LLM Query ChEMBL

## Overview

This skill focuses on running the local ChEMBL Text-to-SQL pipeline, inspecting outputs, and iterating prompts until results match user intent. It is the workflow wrapper around `src/db_llm_query.py` (which delegates to `src/db_llm_query_v1.py`).

## When to Use This Skill

Use this skill when the request involves:

- Running a natural-language query against the local ChEMBL SQLite DB
- Iterating the LLM loop to refine SQL results
- Inspecting CSV outputs or logs to diagnose errors
- Tuning model lists, context thresholds, or judge thresholds
- Orchestrating multiple runs with consistent run labels

## Repo Entry Point (Canonical CLI)

Always use the wrapper:

```bash
uv run python src/db_llm_query.py -q "..."
```

Notes:
- Default SQL model list is `expensive` if neither `--sql-model` nor `--sql-model-list` is provided.
- Default `--min-context` is `100000` for OpenRouter model filtering.
- Default `--filter-profile` is `strict` (publication + confidence = 9 + single protein).
- Use `--run-label` to stamp all outputs and logs with a stable ID.

## Quick Start (Canonical Command)

```bash
RUN_LABEL="query1_kinase_after_2022_$(date +%Y%m%d_%H%M%S)"; \
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py \
  -vv \
  --run-label "${RUN_LABEL}" \
  -f csv \
  -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" \
  |& tee "logs/db_llm_${RUN_LABEL}.log"
```

## Output Layout (Defaults)

- Final CSV (when `-f csv`): `query_results_<run_label>.csv`
- Auto-save CSV (when `--auto`): `query_results_<run_label>.csv` (or `--output-file`)
- Intermediate CSVs (default on): `logs/intermediate/query_results_<run_label>_iter<N>.csv`
- Logs (recommended): `logs/db_llm_<run_label>.log`

## Example Run (Illustrative)

Log excerpt (from `logs/db_llm_<run_label>.log`):

```text
2026-01-15 03:12:01 - __main__ - INFO - Run label: query1_kinase_after_2022_20260115_031201
2026-01-15 03:12:01 - __main__ - INFO - Using provider=openrouter sql_model_list=expensive
2026-01-15 03:12:02 - __main__ - INFO - Iteration 1/20
2026-01-15 03:12:10 - __main__ - INFO - Judge score=0.74 decision=NO
2026-01-15 03:12:10 - __main__ - INFO - Iteration 2/20
2026-01-15 03:12:19 - __main__ - INFO - Judge score=0.93 decision=YES
```

CSV snippet (from `query_results_<run_label>.csv`):

```text
molecule_chembl_id,canonical_smiles,target_chembl_id,target_pref_name,document_year,document_doi,standard_type,standard_value,standard_units
CHEMBL1234,CCN1...,CHEMBL203,EGFR,2023,10.1000/xyz123,IC50,42,nM
CHEMBL5678,COC1...,CHEMBL279,JAK2,2024,10.1000/abc456,IC50,18,nM
```

Note: The excerpt above is illustrative. Actual columns and values depend on the prompt and filters.

## Common Command Patterns

**Strict profile, CSV output, explicit model list:**
```bash
uv run python src/db_llm_query.py \
  --sql-model-list expensive \
  --min-context 100000 \
  --filter-profile strict \
  --run-label "run_strict_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "..."
```

**Relaxed profile (use when strict yields too few results):**
```bash
uv run python src/db_llm_query.py \
  --filter-profile relaxed \
  --run-label "run_relaxed_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "..."
```

**Dry run (show SQL only):**
```bash
uv run python src/db_llm_query.py --dry-run -q "..."
```

**Local-only LLM (no remote provider):**
```bash
uv run python src/db_llm_query.py --no-provider -q "..."
```

## Common Query Recipes

**Kinase inhibitors after 2022 (strict profile):**
```bash
uv run python src/db_llm_query.py \
  --filter-profile strict \
  --run-label "kinase_after_2022_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "return canonical_smiles, molecule_chembl_id, target_pref_name, document_year, document_doi, standard_type, standard_value, standard_units for kinase inhibitors with IC50 in nM, year >= 2022"
```

**Target-centric activities (single target, IC50 only):**
```bash
uv run python src/db_llm_query.py \
  --run-label "egfr_ic50_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "for target CHEMBL203 (EGFR), return molecule_chembl_id, canonical_smiles, standard_type, standard_value, standard_units, pchembl_value, assay_description, document_year"
```

**Compound-centric activities (all assays for a molecule):**
```bash
uv run python src/db_llm_query.py \
  --run-label "compound_acts_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "for molecule CHEMBL25, return target_pref_name, standard_type, standard_value, standard_units, pchembl_value, assay_description, document_year, document_doi"
```

**Relaxed profile for sparse areas:**
```bash
uv run python src/db_llm_query.py \
  --filter-profile relaxed \
  --run-label "relaxed_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "return molecule_chembl_id, canonical_smiles, target_pref_name, document_year, standard_type, standard_value, standard_units for GPCR inhibitors after 2022"
```

## Structure and Similarity Recipes

ChEMBL structures live in `compound_structures` (join on `molregno` to `molecule_dictionary`). The SQLite DB does not provide true chemistry-aware similarity/substructure operators, so use exact matches or heuristic SMILES filters in-SQL; for real similarity, export SMILES and use RDKit outside the DB.

Install RDKit (optional) for similarity work:
```bash
uv sync --extra chemistry
```

### RDKit Install Troubleshooting

- **Wheel not available**: `rdkit-pypi` wheels may not be published for every OS/Python combo. Ensure you're on Python 3.13 and try again later. If wheels are unavailable, skip the similarity step and use exact InChIKey/SMILES matches.
- **Build error**: This repo uses `uv` only. Avoid `pip` or conda. If a build is attempted and fails, it usually means no wheel exists for your platform.
- **Verify import**: Run `uv run python -c "import rdkit; print(rdkit.__version__)"` after install.

**Exact match by InChIKey (best for identity):**
```bash
uv run python src/db_llm_query.py \
  --run-label "inchikey_match_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "find molecules where compound_structures.standard_inchi_key = 'XXXXXXXXXXXXXX-YYYYYYYYYY-Z'. return molecule_dictionary.chembl_id, molecule_dictionary.pref_name, compound_structures.canonical_smiles"
```

**Exact match by canonical SMILES:**
```bash
uv run python src/db_llm_query.py \
  --run-label "smiles_match_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "find molecules with compound_structures.canonical_smiles = 'CC(=O)Oc1ccccc1C(=O)O'. return molecule_dictionary.chembl_id, pref_name"
```

**Heuristic substructure (SMILES substring; may miss/overmatch):**
```bash
uv run python src/db_llm_query.py \
  --run-label "smiles_like_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "find molecules where compound_structures.canonical_smiles LIKE '%c1ccccc1%'. return chembl_id, pref_name, canonical_smiles"
```

**Similarity (two-pass):**
1) Export candidate SMILES from ChEMBL.
```bash
uv run python src/db_llm_query.py \
  --run-label "export_smiles_$(date +%Y%m%d_%H%M%S)" \
  -f csv \
  -q "return molecule_dictionary.chembl_id, compound_structures.canonical_smiles for small molecules with non-null canonical_smiles"
```
2) Run RDKit similarity, then map back by `chembl_id`.
```bash
uv run python .codex/skills/db-llm-query-chembl/scripts/rdkit_similarity.py \
  query_results_<run_label>.csv \
  --query-smiles "CC(=O)Oc1ccccc1C(=O)O" \
  --smiles-col canonical_smiles \
  --id-col chembl_id \
  --top 50 \
  --threshold 0.6
```

## Iteration Workflow (Outer Loop)

1. Confirm the query goal and required columns.
2. Choose a descriptive run label and keep it consistent.
3. Run the CLI with logging and CSV output.
4. Inspect the CSV and logs for errors or misinterpretation.
5. Refine the prompt (filters, joins, units) and rerun.
6. Stop when results match intent; report output locations.

## Prompting Patterns That Work Well

- Ask for explicit fields: `"chembl_id", "canonical_smiles", "standard_type", "standard_value", "standard_units"`
- Constrain measurement type and units: `"IC50 in nM"`
- Specify entity relationships: target -> assay -> activity -> document
- Add year bounds and target classes explicitly

See `references/prompt_patterns.md` for templates.

## Validation Checklist (Post-Run)

- Columns: Are all requested fields present and named correctly?
- Units: Are `standard_units` or `standard_type` aligned to the prompt?
- Filters: Are year bounds and target class constraints enforced?
- Duplicates: Are repeated rows expected (multiple assays) or a join issue?
- Coverage: Do row counts match expectation (too few or too many)?

Use the bundled inspector:

```bash
uv run python .codex/skills/db-llm-query-chembl/scripts/inspect_results.py query_results_<run_label>.csv
```

## Troubleshooting

- **No rows returned**: Switch to `--filter-profile relaxed`, reduce constraints, or increase `--max-retries`.
- **Wrong joins**: Restate relationships explicitly in the prompt (target, assay, activity, document).
- **Missing DOIs**: Ask for document fields and confirm `document` joins in prompt.
- **Slow or timeouts**: Lower `--max-retries` or add limits in prompt.
- **Model errors**: Set `--provider` explicitly and verify API keys (e.g., `OPENROUTER_API_KEY`).

## Failure Modes (Log Cues)

- `OPENROUTER_API_KEY not set; cannot fetch OpenRouter model context.` -> context filtering disabled; results may be noisier.
- `Failed to fetch OpenRouter models for context filtering; using unfiltered list.` -> network/key issue; consider `--provider` and keys.
- `No OpenRouter models meet min_context=...` -> lower `--min-context` or pick a specific `--sql-model`.
- `Invalid TEXT2SQL_PROVIDER=...; falling back to openrouter` -> fix env var or pass `--provider`.
- `All <N> iterations exhausted` -> tighten prompt, reduce joins, or increase `--max-retries`.
- `Error: ...` (stderr) -> inspect `logs/db_llm_<run_label>.log` for stack trace context.

## References and Scripts

- `references/cli_flags.md` - key CLI options and defaults
- `references/output_layout.md` - output file naming rules
- `references/prompt_patterns.md` - prompt templates and refinements
- `scripts/inspect_results.py` - quick CSV inspection with Polars
- `scripts/rdkit_similarity.py` - RDKit Tanimoto similarity helper

## Related Skills

Use `chembl-database` for schema details, table relationships, and domain-specific query patterns.
