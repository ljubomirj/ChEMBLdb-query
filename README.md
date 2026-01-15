# ChEMBLdb Tools

Local utilities for querying the ChEMBL SQLite database with LLM-assisted SQL generation.

## Quick start (uv)
```bash
uv python install 3.13
uv venv --python 3.13
uv sync

uv run python src/db_llm_query.py -q "find kinase inhibitors after 2022"
```

Optional extras:
```bash
uv sync --extra anthropic
uv sync --extra local
```

## Environment setup
Create a `.env` (ignored by git) from the template:
```bash
cp .env.example .env
```
Fill in any of:
```
OPENROUTER_API_KEY=
CEREBRAS_API_KEY=
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
```

## Provider selection
OpenRouter is the default provider. You can override via CLI or env var:
```bash
TEXT2SQL_PROVIDER=deepseek uv run python src/db_llm_query.py -q "..."
```
or
```bash
uv run python src/db_llm_query.py --provider cerebras -q "..."
```

To force local only:
```bash
uv run python src/db_llm_query.py --no-provider -q "..."
```

## Provider reference
See `doc/providers.md` for providers, default models, and model IDs.

## CLI options (db_llm_query.py)
All options are available on `src/db_llm_query.py` (wrapper) and `src/db_llm_query_v1.py`.

Usage patterns:
```bash
uv run python src/db_llm_query.py -q "..."
echo "..." | uv run python src/db_llm_query.py
```

Options and defaults:
- `query` (positional): natural language query. Optional if provided via `-q/--query` or stdin.
- `-q, --query`: natural language query string. Default: unset.
- `--provider`: LLM provider (`auto|anthropic|openrouter|cerebras|deepseek|local`). Default: unset (uses `TEXT2SQL_PROVIDER` or `openrouter`).
- `--no-provider`: disable remote providers (force local LLM). Default: `false`.
- `--db-path`: SQLite DB path. Default: `database/latest/chembl_36/chembl_36_sqlite/chembl_36.db`.
- `-m, --sql-model, --model`: SQL model ID. Default: unset.
- `--sql-model-list, --model-list`: model tier (`cheap|expensive|super|all`). Default: `expensive` (when no `--sql-model` is provided).
- `--sql-model-cycle, --model-cycle`: retry cycling (`random|orderly|cicada`). Default: `cicada`.
- `--judge-model`: judge/prompt-writer model ID. Default: unset.
- `--judge-model-list`: judge tier (`cheap|expensive|super|all`). Default: `expensive`.
- `--judge-model-cycle`: judge cycling (`random|orderly|cicada`). Default: unset (uses SQL cycle).
- `--max-retries`: max iterations. Default: `20`.
- `-t, --timeout`: SQLite timeout seconds. Default: `60`.
- `-a, --auto`: auto-save results to timestamped CSV. Default: `false`.
- `-f, --format`: output format (`json|csv|table`). Default: `table`.
- `-v, --verbose`: verbosity; repeat for more (`-v/-vv/-vvv`). Default: `0`.
  - `-v`: provider request/response dumps; prints full system prompt once at UP_1.
  - `-vv`: includes UP/SQL/RES/J blocks.
  - `-vvv`: includes judge-prompt metadata (sizes/iteration).
- `--dry-run`: show SQL only, do not execute. Default: `false`.
- `--min-rows`: min rows hint for retries. Default: `1`.
- `--history-window`: iterations kept in history. Default: `11`.
- `--judge-score-threshold`: stop if score >= threshold. Default: `0.9`.
- `--judge-call-retries`: retries per judge/prompt-writer call. Default: `3`.
- `--schema-docs-path`: schema docs path. Default: `doc/chembl_database_schema.md`.
- `--schema-sample-rows`: sample rows per table in schema docs. Default: `3`.
- `--schema-max-cell-len`: max cell length for schema docs. Default: `80`.
- `--prompt-hints-path`: full lookup-table hints path. Default: `doc/chembl_prompt_hints.md`.
- `--filter-profile`: prompt-writer preset filters (`strict|relaxed`). Default: `strict`.
- `--output-base`: base filename for CSV outputs. Default: `query_results`.
- `--output-file`: exact filename for CSV outputs (overrides `--output-base`). Default: unset.
- `--min-context`: minimum OpenRouter model context length. Default: `300000`.
- `--intermediate-dir`: directory for intermediate CSV results. Default: `logs/intermediate`.
- `--save-intermediate`: save intermediate CSV results per iteration. Default: `true`.
- `--no-save-intermediate`: disable intermediate CSV results.
- `--run-label`: label used in all run-derived filenames. Default: timestamp.
- `--temperature`: temperature for SQL generation and prompt-writer. Default: `1.0`.
- `--judge-temperature`: temperature for judge model. Default: `0.1`.

## Examples
Example session with verbose output and logging via `tee`:
```bash
PYTHONUNBUFFERED=1 python src/db_llm_query_v1.py -vv -q "" |& tee logs/db_llm_query_$(date +%Y%m%d_%H%M%S).log^C
```

Query used:
```
get the smiles,chembl_id, target_name, publication year, article doi,
and IC50 for all kinase inhibitors published after 2022
and write this into a file called kinase_inhibitors_after_2022.csv
```

Expected answer:
```
CSV file written: kinase_inhibitors_after_2022.csv
Columns: canonical_smiles, molecule_chembl_id, target_name, publication_year, doi, standard_type, standard_value, standard_units
```

CSV filenames:
- With `-a/--auto`, the file name is `{output_base}_YYYYMMDD_HHMMSS.csv` (local time), unless `--output-file` is set.
- With `-f csv` and no `-a`, the file name is `{output_base}_{run_id}.csv` when `--run-label` (or default timestamp) is available, unless `--output-file` is set.
Intermediate results:
- When enabled, intermediate CSVs are saved to `{intermediate_dir}` as `{output_base}_{run_id}_iterN.csv`.
Run labels:
- Use `--run-label` to replace the timestamp used in `{run_id}` for intermediate and auto-saved results.
Judge inputs:
- RES summaries are sent to the judge with `res_mode: sample` or `res_mode: full`. Full rows are only passed when the estimated RES size fits within 90% of the judge model’s context window.

Expected result excerpt (from the reference text):
```
For those interested in the gory details, a Jupyter notebook with code I used to extract and analyze the data is available on GitHub. My search returned 44,992 records, while the Gemini search returned 38,571. Why the difference?
```

Notebook reference:
```
https://github.com/PatWalters/practical_cheminformatics_posts/tree/main/gemini_chembl
```

Reference:
```
https://patwalters.github.io/Searching-ChEMBL-with-Gemini/
```

Equivalent run with a single run label (shared across logs and outputs):
```bash
RUN_LABEL=$(date +%Y%m%d_%H%M%S)
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --run-label "${RUN_LABEL}" -q "get the smiles,chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_query1_${RUN_LABEL}.log"
```

Current canonical query run (descriptive run label + CSV output):
```bash
RUN_LABEL="query1_kinase_after_2022_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --run-label "${RUN_LABEL}" -f csv -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```
