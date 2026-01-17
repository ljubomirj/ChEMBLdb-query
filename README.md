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
DEEPSEEK_API_KEY=
CEREBRAS_API_KEY=
ZAI_API_KEY=
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
- `src/text2sql/openai_direct.py`: OpenAI provider implementation.
- `src/text2sql/base.py`: Base provider interfaces and shared helpers.
- `src/text2sql/openrouter.py`: OpenRouter provider implementation.
- `src/text2sql/deepseek.py`: DeepSeek provider implementation.
- `src/text2sql/cerebras.py`: Cerebras provider implementation.
- `src/text2sql/zai.py`: Z.AI provider implementation.
- `src/text2sql/env.py`: Environment loading and provider config helpers.
- `src/text2sql/local_llm.py`: Local model provider integration.
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
- `--provider`: LLM provider (`auto|anthropic|openai|openrouter|deepseek|cerebras|zai|local`). Default: unset (uses `TEXT2SQL_PROVIDER` or `openrouter`).
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
- `--provider-sleep`: min seconds between LLM API calls. Default: `0`.
- `--provider-retry-backoff`: base seconds for exponential backoff after failed provider calls. Default: `0`.
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
- `--filter-profile`: prompt-writer preset filters (`none|strict|relaxed`). Default: `none`.
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

Expected result excerpt (from the reference text):
```
For those interested in the gory details, a Jupyter notebook with code I used to extract and analyze the data is available on GitHub. My search returned 44,992 records, while the Gemini search returned 38,571. Why the difference?
```

Notebook reference:
[PatWalters/practical_cheminformatics_posts gemini_chembl](https://github.com/PatWalters/practical_cheminformatics_posts/tree/main/gemini_chembl)

Reference:
[Searching ChEMBL with Gemini](https://patwalters.github.io/Searching-ChEMBL-with-Gemini/)

Attempt at equivalent run with a single run label (shared across logs and outputs):

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

Use Cerberas for speed, atm (16-Jan-2026) only top model there available is GLM-4.7:

```bash
$ PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --provider cerebras --sql-model zai-glm-4.7 --judge-model zai-glm-4.7 --filter-profile none -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

Similar query, but confidence filter is not used, so it returns 44K+ rows
```bash
$ wc -l query_results_query1_kinase_after_2022_relaxed_cerebras_20260116_202627.csv
   44914 query_results_query1_kinase_after_2022_relaxed_cerebras_20260116_202627.csv
```

The user prompt (that is created from the user question above) is
```text
Write a SQL query to retrieve the canonical_smiles, chembl_id, target_name (pref_name from target_dictionary), publication year, article doi, and standard IC50 value. Join the activities table with assays, docs, molecule_dictionary, compound_structures, target_dictionary, target_components, component_class, and protein_classification tables. Filter for activities where the standard_type is 'IC50' and the document year is greater than 2022. Restrict the results to targets where the protein_classification.pref_name contains 'Kinase'. Do not apply any filters on doc_type or confidence_score.
```

The SQL generated was
```sql
SELECT
    compound_structures.canonical_smiles,
    molecule_dictionary.chembl_id,
    target_dictionary.pref_name AS target_name,
    docs.year,
    docs.doi,
    activities.standard_value AS IC50
FROM activities
JOIN assays ON activities.assay_id = assays.assay_id
JOIN docs ON assays.doc_id = docs.doc_id
JOIN molecule_dictionary ON activities.molregno = molecule_dictionary.molregno
JOIN compound_structures ON molecule_dictionary.molregno = compound_structures.molregno
JOIN target_dictionary ON assays.tid = target_dictionary.tid
JOIN target_components ON target_dictionary.tid = target_components.tid
JOIN component_class ON target_components.component_id = component_class.component_id
JOIN protein_classification ON component_class.protein_class_id = protein_classification.protein_class_id
WHERE activities.standard_type = 'IC50'
  AND docs.year > 2022
  AND protein_classification.pref_name LIKE '%Kinase%'
```

The judge thought of the user question, prompt, the sql, and the rows sampled from the result
```json
{
  "analysis": "The SQL query correctly retrieves the requested columns (canonical_smiles, chembl_id, target_name, year, doi, IC50) and applies appropriate
 filters: standard_type='IC50', year>2022, and protein_classification.pref_name LIKE '%Kinase%'. The joins correctly connect activities to assays, docs, m
olecule_dictionary, compound_structures, target_dictionary, target_components, component_class, and protein_classification. The sample results show valid
kinase targets with IC50 values from 2023 publications. The query interpretation is reasonable - 'kinase inhibitors' is interpreted as IC50 activities aga
inst kinase targets, which is standard practice. No LIMIT clause was used, and all requested fields are present.",
  "score": 1.0,
  "decision": "YES"
}
```

Big log file! :-)
```bash
$ l logs/db_llm_query1_kinase_after_2022_relaxed_cerebras_20260116_202627.log
-rw-------@ 1 ljubomir  staff   6.3M 16 Jan 23:04 logs/db_llm_query1_kinase_after_2022_relaxed_cerebras_20260116_202627.log
```

(NB the label has `relaxed` in but that is in error, the filtering is none, not `relaxed`)

Using a Z.AI API using GLM-4.7 model that way

```bash
RUN_LABEL="query1_kinase_after_2022_zai_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --provider zai --sql-model glm-4.7 --judge-model glm-4.7 --filter-profile none -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

The result is 38K+
```bash
$ wc -l query_results_query1_kinase_after_2022_zai_20260116_231554.csv
   38487 query_results_query1_kinase_after_2022_zai_20260116_231554.csv
```

The SQL quary is
```sql
SELECT
    compound_structures.canonical_smiles,
    molecule_dictionary.chembl_id,
    target_dictionary.pref_name AS target_name,
    docs.year,
    docs.doi,
    activities.standard_value AS IC50
FROM
    molecule_dictionary
JOIN
    compound_structures ON molecule_dictionary.molregno = compound_structures.molregno
JOIN
    activities ON molecule_dictionary.molregno = activities.molregno
JOIN
    assays ON activities.assay_id = assays.assay_id
JOIN
    target_dictionary ON assays.tid = target_dictionary.tid
JOIN
    docs ON assays.doc_id = docs.doc_id
WHERE
    docs.year > 2022
    AND activities.standard_type = 'IC50'
    AND target_dictionary.pref_name LIKE '%kinase%'
```

The judge judgement accepting
```json
{"analysis":"The SQL query correctly implements the user's request. It joins the necessary tables (molecule_dictionary, compound_structures, activities, assays, target_dictionary, docs), returns all requested columns (canonical_smiles, chembl_id, target_name, year, doi, IC50), and applies the specified filters (year > 2022, standard_type = 'IC50', target_name contains 'kinase'). The query does not include an arbitrary LIMIT clause. The sample results (38,486 total rows, stratified by year) show the correct structure and data, with all target names containing 'kinase', years of 2023, and valid IC50 values. The filtering by 'kinase' in the target name is the standard approach for identifying kinase-related targets in ChEMBL. While one could argue that action_type filtering (INHIBITOR) might be more precise for 'inhibitors', the UP did not request this and the LIKE '%kinase%' filter on target name is the typical way to identify kinase targets. The query is correct and complete.","score":0.95,"decision":"YES"}
```

Log file 
```bash
$ l logs/db_llm_query1_kinase_after_2022_zai_20260116_231554.log
-rw-------@ 1 ljubomir  staff   5.6M 16 Jan 23:18 logs/db_llm_query1_kinase_after_2022_zai_20260116_231554.log
```

Back to OpenRouter API using PAYG credits
```bash
$ RUN_LABEL="query1_kinase_after_2022_openrouter_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

Returned 41K+ rows for the result in iteration 2
```bash
$ wc -l query_results_query1_kinase_after_2022_openrouter_20260116_233251.csv
   41383 query_results_query1_kinase_after_2022_openrouter_20260116_233251.csv
```

The final SQL query
```sql
WITH kinase_tids AS (
  SELECT DISTINCT tc.tid
  FROM target_components tc
  JOIN component_class cc ON cc.component_id = tc.component_id
  JOIN protein_classification pc ON pc.protein_class_id = cc.protein_class_id
  WHERE LOWER(pc.pref_name) LIKE '%kinase%'
)
SELECT
  cs.canonical_smiles AS smiles,
  md.chembl_id AS compound_chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi AS doi,
  act.standard_value AS ic50_value,
  act.standard_units AS ic50_units
FROM activities act
JOIN assays ass ON ass.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = ass.tid
JOIN kinase_tids kt ON kt.tid = td.tid
JOIN molecule_dictionary md ON md.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN docs d ON d.doc_id = COALESCE(ass.doc_id, act.doc_id)
WHERE act.standard_type = 'IC50'
  AND d.year > 2022
ORDER BY
  publication_year DESC,
  (ic50_value IS NULL) ASC,
  ic50_value ASC;
```

The judge-ment accepting the result in iteration 2.
```json
2026-01-16 23:34:48,364 - text2sql.openrouter - INFO - ITER_2 > J_2 - OpenRouter API call: 215085 prompt + 491 completion = 215576 total tokens
📄 Intermediate saved to: logs/intermediate/query_results_query1_kinase_after_2022_openrouter_20260116_233251_iter2.csv
--------------------
J_2:
{"analysis":"RES_2 correctly applies the kinase-target definition via component_class/protein_classification, filters IC50 records from docs.year>2022, joins docs using COALESCE(assays.doc_id, activities.doc_id) as required, returns the specified seven columns in order, omits any LIMIT, and sorts by publication_year DESC, then ic50_value nullness and value as requested. Sample rows confirm the intent. No issues found.","score":0.98,"decision":"YES"}
--------------------
2026-01-16 23:34:48,377 - db_llm_query_v1 - INFO - ITER_2 - Stopping: judge_decision=True judge_score=0.98
```

In the initial iteration 1, the SQL query was somewhat different
```sql
WITH kinase_tids AS (
  SELECT DISTINCT tc.tid
  FROM target_components tc
  JOIN component_class cc
    ON cc.component_id = tc.component_id
  JOIN protein_classification pc
    ON pc.protein_class_id = cc.protein_class_id
  WHERE LOWER(pc.pref_name) LIKE '%kinase%'
)
SELECT
  cs.canonical_smiles AS smiles,
  md.chembl_id AS compound_chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi AS doi,
  act.standard_value AS ic50_value,
  act.standard_units AS ic50_units
FROM activities act
JOIN assays ass
  ON ass.assay_id = act.assay_id
JOIN target_dictionary td
  ON td.tid = ass.tid
JOIN kinase_tids kt
  ON kt.tid = td.tid
JOIN molecule_dictionary md
  ON md.molregno = act.molregno
JOIN compound_structures cs
  ON cs.molregno = md.molregno
JOIN docs d
  ON d.doc_id = COALESCE(act.doc_id, ass.doc_id)
WHERE act.standard_type = 'IC50'
  AND d.year > 2022
ORDER BY
  publication_year DESC,
  ic50_value IS NULL ASC,
  ic50_value ASC;
```

But the query and the result were rejected by the judge on the grounds of:
```json
{"analysis":"RES_1 largely matches the requested output columns and filters (IC50 only, docs.year > 2022, kinase targets via protein_classification name contains 'kinase', no LIMIT, ordered by year desc then value asc with NULLs last). However, the SQL joins docs using COALESCE(act.doc_id, ass.doc_id), which prioritizes activities.doc_id over assays.doc_id. The instructions explicitly say to join docs using assays.doc_id (and only coalesce with activities.doc_id if needed), so the coalesce order should be COALESCE(ass.doc_id, act.doc_id). Using the reversed order can attach the wrong publication year/DOI to an assay/activity when activities.doc_id is populated but differs from the assay document. Fix: change the docs join to prefer ass.doc_id, and keep the year filter on that joined docs row.","score":0.85,"decision":"NO"}
```
OpenAI provider added - runs
```bash
ljubomir@macbook2(::main):~/ChEMBLdb-query$ RUN_LABEL="query1_kinase_after_2022_openai_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vvv --provider openai -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"^C
```

...but only 21K+ lines of result returned - TBD debug
```bash
ljubomir@macbook2(::main):~/ChEMBLdb-query$ wc -l query_results_query1_kinase_after_2022_openai_20260117_170659.csv
   21339 query_results_query1_kinase_after_2022_openai_20260117_170659.csv
ljubomir@macbook2(::main):~/ChEMBLdb-query$ l logs/db_llm_query1_kinase_after_2022_openai_20260117_170659.log
-rw-------@ 1 ljubomir  staff   4.1M 17 Jan 17:07 logs/db_llm_query1_kinase_after_2022_openai_20260117_170659.log
```

The judgement was
```json
2026-01-17 17:07:36,373 - db_llm_query_v1 - DEBUG - ITER_1 - J_1:
{"analysis":"SQL follows instructions: correct columns and aliases, deduplicated via ROW_NUMBER over the required key, filters exactly match the user’s profile (IC50, non-null standard_value, DOI, year > 2022, kinase targets), and ordering is year DESC then IC50 ascending. Result set is large but sample mode is acceptable. Minor future refinement could remove the redundant IS NOT NULL predicate on target_name, though it doesn’t affect correctness.","score":0.94,"decision":"YES"}
```

for SQL
```sql
WITH ranked AS (
    SELECT
        cs.canonical_smiles AS smiles,
        md.chembl_id,
        td.pref_name AS target_name,
        d.year AS publication_year,
        d.doi,
        act.standard_value AS ic50_value,
        act.standard_units AS ic50_units,
        ROW_NUMBER() OVER (
            PARTITION BY md.chembl_id, td.pref_name, d.year, act.standard_value, act.standard_units
            ORDER BY act.activity_id
        ) AS rn
    FROM activities AS act
    JOIN assays AS a ON act.assay_id = a.assay_id
    JOIN target_dictionary AS td ON a.tid = td.tid
    JOIN docs AS d ON a.doc_id = d.doc_id
    JOIN molecule_dictionary AS md ON act.molregno = md.molregno
    JOIN compound_structures AS cs ON md.molregno = cs.molregno
    WHERE act.standard_type = 'IC50'
      AND act.standard_value IS NOT NULL
      AND d.year > 2022
      AND d.doi IS NOT NULL
      AND td.pref_name IS NOT NULL
      AND LOWER(td.pref_name) LIKE '%kinase%'
)
SELECT
    smiles,
    chembl_id,
    target_name,
    publication_year,
    doi,
    ic50_value,
    ic50_units
FROM ranked
WHERE rn = 1
ORDER BY publication_year DESC, ic50_value ASC;
```

from User Prompt
```text
Return a result set containing the following columns in this order: compound canonical_smiles (rename to smiles), molecule_dictionary.chembl_id, target_dictionary.pref_name (rename to target_name), docs.year AS publication_year, docs.doi, and activities.standard_value AS ic50_value with activities.standard_units AS ic50_units. Use activities joined through assays to target_dictionary (assays.tid) and docs (assays.doc_id), and to molecule_dictionary plus compound_structures (molregno). Filter rows to: activities.standard_type = 'IC50'; activities.standard_value IS NOT NULL; docs.year > 2022; docs.doi IS NOT NULL; target_dictionary.pref_name ILIKE '%kinase%' (to capture kinase targets). Do not add other filters (respect provided filter profile). Deduplicate on (chembl_id, target_name, publication_year, ic50_value, ic50_units). Order results by docs.year DESC, then activities.standard_value ASC.
```

Having Anthropic as provider runs too
```bash
RUN_LABEL="query1_kinase_after_2022_anthropic_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --provider anthropic -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

Got ~41K rows back
```bash
ljubomir@macbook2(::main):~/ChEMBLdb-query$ wc -l query_results_query1_kinase_after_2022_anthropic_20260117_091522.csv
   40818 query_results_query1_kinase_after_2022_anthropic_20260117_091522.csv
ljubomir@macbook2(::main):~/ChEMBLdb-query$ l logs/*anthropic_20260117_091522*
-rw-------@ 1 ljubomir  staff   7.0M 17 Jan 09:26 logs/db_llm_query1_kinase_after_2022_anthropic_20260117_091522.log
```

The SQL query was
```sql
====================
Generated SQL_3 (claude-sonnet-4.5):
====================
WITH kinase_target_ids AS (
  SELECT DISTINCT td.tid
  FROM target_dictionary td
  INNER JOIN target_components tc ON td.tid = tc.tid
  INNER JOIN component_class cc ON tc.component_id = cc.component_id
  INNER JOIN protein_classification pc ON cc.protein_class_id = pc.protein_class_id
  WHERE pc.pref_name LIKE '%kinase%'
)
SELECT
  cs.canonical_smiles,
  cil.chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi,
  a.standard_value AS ic50_value
FROM activities a
INNER JOIN assays ass ON a.assay_id = ass.assay_id
INNER JOIN docs d ON ass.doc_id = d.doc_id
INNER JOIN target_dictionary td ON ass.tid = td.tid
INNER JOIN molecule_dictionary md ON a.molregno = md.molregno
INNER JOIN compound_structures cs ON md.molregno = cs.molregno
INNER JOIN chembl_id_lookup cil ON md.molregno = cil.entity_id AND cil.entity_type = 'COMPOUND'
WHERE a.standard_type = 'IC50'
  AND a.standard_value IS NOT NULL
  AND d.year > 2022
  AND ass.tid IN (SELECT tid FROM kinase_target_ids)
ORDER BY d.year DESC, a.standard_value ASC
====================
```

Gemini API via gemini provider also works - but seems I run of quota on the free tier too fast for it to be useful. Still - leaving this Gemini variant here for future reference:
```bash
RUN_LABEL="query1_kinase_after_2022_gemini_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vvv --provider gemini -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

Example session with verbose output and logging via `tee`:
```bash
PYTHONUNBUFFERED=1 python src/db_llm_query_v1.py -vv -q "" |& tee logs/db_llm_query_$(date +%Y%m%d_%H%M%S).log
```

```bash
RUN_LABEL=$(date +%Y%m%d_%H%M%S)
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --run-label "${RUN_LABEL}" -q "get the smiles,chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_query1_${RUN_LABEL}.log"
```


