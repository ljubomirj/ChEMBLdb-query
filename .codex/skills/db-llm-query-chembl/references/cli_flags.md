# CLI Flags (db_llm_query_v1)

Key flags and defaults from `src/db_llm_query_v1.py`.

## Query input

- `-q, --query`: Natural language query string.
- Positional `query`: Alternative to `-q` (or provide via stdin).

## Provider selection

- `--provider {auto,anthropic,openrouter,cerebras,deepseek,local}`: LLM provider (default: `openrouter` or `TEXT2SQL_PROVIDER`).
- `--no-provider`: Force local provider.

## SQL model selection

- `--sql-model, -m`: Explicit SQL model.
- `--sql-model-list`: Model list category (`cheap`, `expensive`, `super`, `all`).
- `--sql-model-cycle`: Cycle method (`random`, `orderly`, `cicada`; default: `cicada`).

## Judge/prompt-writer selection

- `--judge-model`: Explicit judge/prompt-writer model.
- `--judge-model-list`: Model list category (default: `expensive`).
- `--judge-model-cycle`: Cycle method (default: same as SQL cycle).

## Execution controls

- `--max-retries`: Iterations (default: `20`).
- `-t, --timeout`: Query timeout in seconds (default: `600`).
- `--history-window`: Iterations kept in context (default: `11`).
- `--judge-score-threshold`: Stop if score >= threshold (default: `0.9`).
- `--judge-call-retries`: Retries per judge call (default: `3`).
- `--min-rows`: Hint for minimum row count (default: `1`).
- `--dry-run`: Show SQL only, do not execute.

## Schema and prompt hints

- `--schema-docs-path`: Schema cache path (default: `doc/chembl_database_schema.md`).
- `--schema-sample-rows`: Sample rows per table (default: `3`).
- `--schema-max-cell-len`: Max cell length in schema docs (default: `80`).
- `--prompt-hints-path`: Prompt hints path (default: `doc/chembl_prompt_hints.md`).

## Filtering presets

- `--filter-profile {strict,relaxed}`: Prompt-writer filter profile (default: `strict`).
  - `strict`: publication + confidence=9 + single protein
  - `relaxed`: no doc/doi constraint, confidence >= 8

## Output and logging

- `-f, --format {json,csv,table}`: Output format (default: `table`).
- `-a, --auto`: Auto-save results to CSV.
- `--output-base`: Base CSV name (default: `query_results`).
- `--output-file`: Exact filename (overrides `--output-base`).
- `--intermediate-dir`: Intermediate CSV directory (default: `logs/intermediate`).
- `--save-intermediate` / `--no-save-intermediate`: Toggle intermediate CSVs (default: on).
- `--run-label`: Label used in output filenames (default: timestamp).

## Context and temperature

- `--min-context`: Minimum OpenRouter context length (default: `300000`).
- `--temperature`: SQL + prompt-writer temperature (default: `1.0`).
- `--judge-temperature`: Judge temperature (default: `0.1`).

## Verbosity

- `-v, -vv, -vvv`: Increase logging verbosity.
