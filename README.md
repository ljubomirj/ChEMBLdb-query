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
Then open `.env` and add the missing API keys (the template placeholders are blank). Fill in any of:
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

## Agentic files and directories
- `AGENTS.md`: repo-specific agent instructions; includes the copied global CLAUDE learning-loop text so the requirement is visible to anyone who checks out the repo.
- `.claude/LEARNINGS.md`: per-repo learning log required by global agent instructions.
- `.claude/skills`: symlink to `.codex/skills`.
- `.codex/skills/`: skill definitions used by agents:
  - `chembl-database/` (schema/query guidance, references, and scripts)
  - `db-llm-query-chembl/` (outer-loop `db_llm_query.py` runner guidance)
- `db-llm-query-chembl.skill`: packaged skill artifact.
- Note: there is no repo-local `CLAUDE.md` in this tree (some setups use a user-level global `CLAUDE.md`).

Acknowledgement: created with the codex-5.2-high agent.

## Public release file inventory (as of 2026-01-15)
This list reflects files intended for the public repo. Excluded: local `.env` files (except `.env.example`), `.venv/`, `.git*`, editor swap/backup files, `__pycache__/`/`*.pyc`, and temp files. Some logs and run outputs are intentionally included.

- `.claude/LEARNINGS.md`: Per-repo learning log required by global agent instructions.
- `.codex/skills/chembl-database/SKILL.md`: Skill definition and workflow notes for ChEMBL database querying.
- `.codex/skills/chembl-database/references/api_reference.md`: Reference notes for the chembl-database skill.
- `.codex/skills/chembl-database/scripts/example_queries.py`: Example ChEMBL query snippets for the skill.
- `.codex/skills/db-llm-query-chembl/SKILL.md`: Skill definition and workflow guidance for running db_llm_query.
- `.codex/skills/db-llm-query-chembl/references/cli_flags.md`: Reference for db_llm_query CLI flags and defaults.
- `.codex/skills/db-llm-query-chembl/references/output_layout.md`: Reference for output file naming and layout.
- `.codex/skills/db-llm-query-chembl/references/prompt_patterns.md`: Prompt templates for reliable Text-to-SQL results.
- `.codex/skills/db-llm-query-chembl/scripts/inspect_results.py`: Polars-based CSV inspector for query outputs.
- `.codex/skills/db-llm-query-chembl/scripts/rdkit_similarity.py`: RDKit similarity helper for SMILES-based exports.
- `.env.example`: Template environment file with provider API key placeholders.
- `.python-version`: Python version pin for tooling (3.13).
- `AGENTS.md`: Repo-specific agent instructions and policies.
- `README.md`: Primary project documentation and CLI usage notes.
- `database/INSTALL`: Instructions for downloading and unpacking ChEMBLdb releases.
- `db-llm-query-chembl.skill`: Packaged skill artifact for agent tooling.
- `doc/AGENTS_TEXT2CHEMBL.md`: Guidance for agent prompts and text-to-ChEMBL conventions.
- `doc/chembl_database_schema.md`: Cached schema docs (tables/columns/sample rows) for the SQLite DB.
- `doc/chembl_prompt_hints.md`: Prompt hints and lookup tables to steer LLM SQL generation.
- `doc/providers.md`: Provider reference and model lists.
- `logs/db_llm_query1_kinase_after_2022_relaxed_20260115_052049.log`: Run log captured from 'db_llm_query1_kinase_after_2022_relaxed_20260115_052049'.
- `logs/intermediate/query_results_query1_kinase_after_2022_relaxed_20260115_052049_iter1.csv`: Intermediate CSV for run label 'query1_kinase_after_2022_relaxed_20260115_052049' (iteration 1).
- `pyproject.toml`: Project metadata and dependency definitions.
- `query_results_query1_kinase_after_2022_relaxed_20260115_052049.csv`: Final CSV output for run label 'query1_kinase_after_2022_relaxed_20260115_052049'.
- `src/db_llm_query.py`: Stable wrapper entry point for the LLM query CLI.
- `src/db_llm_query_v1.py`: Main Text-to-SQL pipeline implementation (v1).
- `src/text2sql/ANTHROPIC_PROVIDER.md`: Provider-specific notes for Anthropic integration.
- `src/text2sql/__init__.py`: Text2SQL package initializer.
- `src/text2sql/anthropic_direct.py`: Anthropic provider implementation.
- `src/text2sql/base.py`: Base provider interfaces and shared helpers.
- `src/text2sql/cerebras.py`: Cerebras provider implementation.
- `src/text2sql/deepseek.py`: DeepSeek provider implementation.
- `src/text2sql/env.py`: Environment loading and provider config helpers.
- `src/text2sql/local_llm.py`: Local model provider integration.
- `src/text2sql/openrouter.py`: OpenRouter provider implementation.
- `uv.lock`: Locked dependency versions for uv.

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
- `-t, --timeout`: SQLite timeout seconds. Default: `600`.
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
- `--min-context`: minimum OpenRouter model context length. Default: `100000`.
- `--intermediate-dir`: directory for intermediate CSV results. Default: `logs/intermediate`.
- `--save-intermediate`: save intermediate CSV results per iteration. Default: `true`.
- `--no-save-intermediate`: disable intermediate CSV results.
- `--run-label`: label used in all run-derived filenames. Default: timestamp.
- `--temperature`: temperature for SQL generation and prompt-writer. Default: `1.0`.
- `--judge-temperature`: temperature for judge model. Default: `0.1`.

## Examples
Most recent recommended run (relaxed filter + long context + CSV + logs):
```bash
unset OPENROUTER_API_KEY && set -a && source ./.env && set +a && RUN_LABEL="query1_kinase_after_2022_relaxed_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --min-context=100000 --filter-profile relaxed --run-label "${RUN_LABEL}" -f csv -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_query1_${RUN_LABEL}.log"
```

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
[PatWalters/practical_cheminformatics_posts gemini_chembl](https://github.com/PatWalters/practical_cheminformatics_posts/tree/main/gemini_chembl)

Reference:
[Searching ChEMBL with Gemini](https://patwalters.github.io/Searching-ChEMBL-with-Gemini/)

Attempt at equivalent run with a single run label (shared across logs and outputs):
```bash
RUN_LABEL=$(date +%Y%m%d_%H%M%S)
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --run-label "${RUN_LABEL}" -q "get the smiles,chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_query1_${RUN_LABEL}.log"
```

Current canonical query run (descriptive run label + CSV output):
```bash
RUN_LABEL="query1_kinase_after_2022_relaxed_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --min-context=100000 --filter-profile relaxed --run-label "${RUN_LABEL}" -f csv -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```
The result .csv. table
```bash
./query_results_query1_kinase_after_2022_relaxed_20260115_052049.csv
```

The log file with everything going on, the queries, the responses, the system context with database schema, the user prompts, the SQL returned by the LLM call, the result of running the SQL on the database, is 
```bash
./logs/db_llm_query1_kinase_after_2022_relaxed_20260115_052049.log
```

If there are multiple iterations, their results will be in dir ./logs/intermediate
```bash
./logs/intermediate/query_results_query1_kinase_after_2022_relaxed_20260115_052049_iter1.csv
```
By default OpenRouter models are the more expensive higher quality models.

For good value, quality at not to big a price, example call using DeepSeek API only. Where SQL writer = deepseek-chat, judge = deepseek-reasoner:

```bash
DEEPSEEK_API_KEY="your_key_here" \
RUN_LABEL="query1_kinase_after_2022_relaxed_deepseek_$(date +%Y%m%d_%H%M%S)"; \
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv \
  --provider deepseek \
  --sql-model deepseek-chat \
  --judge-model deepseek-reasoner \
  --filter-profile relaxed -f csv --run-label "${RUN_LABEL}" \
  -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" \
  |& tee "logs/db_llm_${RUN_LABEL}.log"
```

This avoids OpenRouter entirely by forcing --provider deepseek and uses the DeepSeek models directly.

