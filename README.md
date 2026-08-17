# ChEMBLdb Tools

Local utilities for querying the ChEMBL SQLite database with LLM-assisted SQL generation.

## Latest status first — July 2026
### First full local LLM run — Qwen3.6-27B Hipfire on AMD 7900 XTX (July 2026)

The first **100% local** end-to-end evaluation of the full 1,010-case ChEMBL benchmark. A single model — Qwen3.6-27B (4-bit quantized, 262K context) — performed all three LLM roles (UP writer, SQL generator, judge) on a consumer AMD RX 7900 XTX GPU via the Hipfire feature-daemon. No cloud API calls were made.

| Split | Cases | Pass | Pass rate | Mean score |
|---|---:|---:|---:|---:|
| train | 742 | 237 | 0.319 | 0.777 |
| val | 130 | 40 | 0.308 | 0.767 |
| test | 138 | 44 | 0.319 | 0.772 |
| **total** | **1010** | **321** | **0.318** | **0.775** |

Iteration profile: **87.7% of cases resolved in a single iteration** (mean 1.19 iterations per case). Zero API cost; ~5 days wall time at 7.8 cases/hour.

| vs. cloud baseline (April 2026, GLM-4.7) | Pass rate | Mean score |
|---|---:|---:|
| Cloud GLM-4.7 | 34.7% | 0.788 |
| Local Qwen3.6-27B | 31.8% | 0.775 |
| **Delta** | **−2.9 pp** | **−0.013** |

A 4-bit-quantized 27B model running entirely on a consumer GPU achieves roughly **92% of the cloud model's pass rate** at zero API cost.

Key learnings:
- 88% of cases resolve on first iteration — the model handles most ChEMBL join paths correctly out of the box
- The 48% of cases scoring 0.50–0.90 represent "almost right" SQL with column alias drift, extra columns, or slight row-count differences
- The local Qwen judge is too lenient (accepts 100% of non-empty results); the deterministic scorer is the true benchmark authority
- A grammar fix was required mid-run: the permissive `answer ::= .+` GBNF allowed truncated JSON; a balanced JSON-object grammar eliminated the issue

Reports and documentation:
- **Run report:** [`doc/2026-07-29-hipfire-qwen36-27b-1010-run-report.md`](doc/2026-07-29-hipfire-qwen36-27b-1010-run-report.md)
- **Baseline comparison:** [`doc/2026-07-29-hipfire-qwen36-27b-1010-baseline-comparison.md`](doc/2026-07-29-hipfire-qwen36-27b-1010-baseline-comparison.md)
- **Artifact guide:** [`doc/2026-07-29-hipfire-qwen36-27b-1010-artifact-guide.md`](doc/2026-07-29-hipfire-qwen36-27b-1010-artifact-guide.md)
- **Algorithm description:** [`doc/v5-judge-loop-algorithm.md`](doc/v5-judge-loop-algorithm.md)
- **Full artifact tree:** `runs/qwen36-27b-hipfire-local-full-1010/`

### v5.1010 diversified benchmark is now the active corpus

The project has moved past the old undiversified `1000` corpus. The active benchmark/data shorthand is now:

- **`1010`** = the diversified, balanced v5 corpus
- split file: `cases/v5.1010/splits/case_splits_v5.1010.json`
- dataset report: `experiments/v5.1010_dataset_report.md`
- v5 manifest root: `cases/v5.1010/cases/`
- latest full judge-loop baseline:
  - eval root: `runs/v5_1010_full_judge_loop_20260409_101200/`
  - report: `runs/v5_1010_full_judge_loop_20260409_101200/report.json`

Current full-1010 baseline summary (`prompt_pack_v5.0.yaml`, full J-Judge loop):

| Split | Cases | Pass | Pass rate | Mean score |
|---|---:|---:|---:|---:|
| train | 742 | 264 | 0.355795 | 0.791916 |
| val | 130 | 44 | 0.338462 | 0.771858 |
| test | 138 | 42 | 0.304348 | 0.782109 |
| **total** | **1010** | **350** | **0.346535** | **0.787994** |

Notes:
- `report.json` now includes stable `ordinal` numbers `1..1010` for every case.
- the full run completed with `n_incomplete = 0`
- this is the first completed baseline on the diversified `1010` corpus

### What “balanced / diversified 1010” means here

The `1010` dataset was built from the old `v5.0_balanced` starting point plus additional recovered/diversified cases until the corpus exceeded one thousand cases in a clean, memorable way.

Dataset facts:

- base registry entries examined: `982`
- final target size reached: `1010`
- old `v4.7 1000` corpus reused directly: **no**
- recovered missing manifests: `2`
- copied manifests with patched optional artifacts: `41`
- added document-heavy diversified cases: `35`

Family mix:

| Family | Cases |
|---|---:|
| assay_exact | 147 |
| document | 272 |
| metabolism | 30 |
| other | 237 |
| salts | 24 |
| target_pchembl | 300 |

This is still not perfectly uniform, but it is materially less distorted than the older target-pChEMBL-heavy expansion corpora.

### Case lists and examples

Where to find the full ordered case list:

- canonical ordered list with outcomes and ordinals:  
  `runs/v5_1010_full_judge_loop_20260409_101200/report.json`
- train/val/test membership list:  
  `cases/v5.1010/splits/case_splits_v5.1010.json`

Representative examples from the live 1010 report:

- `#1` train / `web_scrape_hq` / `(+/_)_tylophorine_non_protein_target_ic50_salts` → `partial`, score `0.630769`
- `#2` train / `web_scrape_hq` / `(+/_)_tylophorine_raw264.7_ic50_salts` → `partial`, score `0.484615`
- `#3` train / `web_scrape_hq` / `abhik_human_sub50nm_single_protein_first200` → `pass`, score `1.0`
- `#743` val / `web_scrape_hq` / `approved_drugs_indication_chronic_kidney_disease` → `partial`, score `0.65493`
- `#873` test / `web_scrape_hq` / `afatinib_egfr_ic50_salts` → `pass`, score `1.0`
- `#1010` test / `web_scrape_hq` / `tofacitinib_jak2_ic50_salts` → `pass`, score `1.0`

### v5 codebase direction

The active design direction is the **v5 codebase**, which separates:

1. **forward query generation**
2. **backward reconstruction / curation**
3. **deterministic benchmark evaluation**
4. **prompt optimization / GEPA**

Core v5 surfaces:

- runtime / provider orchestration: `src/db_llm_runtime_v5.py`
- forward artifact logic: `src/db_llm_v5/`
- full judge-loop evaluator: `scripts/evaluate_v5_forward_judge_loop.py`
- design notes: `doc/v5_design.md`

The v5 forward pipeline uses explicit staged artifacts:

- `UQ` → surface user question
- `UP` → execution-oriented semantic plan
- `SQL` → executable SQLite query
- `RES` → result table
- `J` → iterative judge used for “stop / continue”, **not** for benchmark truth

The intended v5 backward/data-synthesis path is equally important:

- `SQL -> UP_exec`
- `UP_exec -> UQ_surface`
- optional `SQL + RES -> intent sketch`

That split matters because the repo is no longer only about one-shot forward querying; it is also about:

- curating better benchmark/data cases
- synthesizing realistic surface questions from executable semantics
- supporting forward/backward loops over the same artifact graph

### Provider state used for v5 work

For current v5 database work the intended provider order is:

1. **Primary:** Z.AI Anthropic-compatible `glm-4.7`
2. **Fallback:** remote llama.cpp / `nemotron-cascade-2-30b-a3b` at `http://192.168.1.251:8081`

Recent v5 runtime changes:

- 1-hour retry cadence for returning from fallback to primary
- 1-hour fallback reprobe cadence
- runtime logs now report the **actual active provider/model**
- INFO logs now include a small RES sample table
- long screen jobs should be launched with `tee` so logs are both visible and persisted

### Important current takeaways

- the diversified `1010` corpus is now real and usable end-to-end
- the full v5 judge-loop baseline has been established on all 1010 cases
- the pass rate is currently modest (~34.65%), so the next practical focus is failure analysis and prompt / loop improvement rather than more corpus growth first
- documentation and reports should be treated **latest-first**: new state at the top, older historical notes below

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
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
CEREBRAS_API_KEY=
ANTHROPIC_API_KEY=
ZAI_API_KEY=
GEMINI_API_KEY=
```

## Examples

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

Attempts below at equivalent runs with a single run label shared across logs and outputs.

## V3 Latest (Feb-2026)

Using up PAYG tokens got expensive real quick for a hobbyist trial&error-s. Decided to attack the issue two prong:

1) Use openrouter free models available atm (Feb-2026). To reproduce - register free account, get a key, put it in the OPENROUTER_API_KEY env var.

```bash
RUN_LABEL="query1_kinase_after_2022_openrouter-free-mesh_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --multi-endpoint-profile openrouter-free-mesh -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

ljubomir@macbook2(::main):~/ChEMBLdb-query$ wc -l query_results*202602*.csv
   38058 query_results_query1_kinase_after_2022_openrouter-free-mesh_20260207_000745.csv
   36738 query_results_query1_kinase_after_2022_openrouter-free-mesh_20260207_091645.csv

SQL used in those two OpenRouter-free runs (from logs):

- 2026-02-07 00:12:01 (openrouter-free-mesh_20260207_000745; chosen: openrouter/free) [log](logs/db_llm_query1_kinase_after_2022_openrouter-free-mesh_20260207_000745.log):

```sql
SELECT cs.canonical_smiles, md.chembl_id, td.pref_name AS target_name, d.year AS publication_year, d.doi AS article_doi, a.standard_value AS IC50 FROM activities a INNER JOIN assays ass ON a.assay_id = ass.assay_id INNER JOIN target_dictionary td ON ass.tid = td.tid INNER JOIN docs d ON ass.doc_id = d.doc_id INNER JOIN molecule_dictionary md ON a.molregno = md.molregno INNER JOIN compound_structures cs ON a.molregno = cs.molregno WHERE td.pref_name LIKE '%kinase%' AND d.year > 2022 AND a.standard_type = 'IC50' AND a.standard_value IS NOT NULL;
```

Judgement J_1:
```json
{"analysis": "The RES_1 table successfully answers the user's question by providing canonical_smiles, chembl_id, target_name, publication_year, article_doi, and IC50 values for kinase inhibitors published after 2022. The SQL joins the correct tables (activities, assays, target_dictionary, docs, molecule_dictionary, compound_structures) with appropriate filters (td.pref_name LIKE '%kinase%', d.year > 2022, a.standard_type = 'IC50'). Sample rows confirm valid kinase targets (e.g., 'Casein kinase I isoform gamma-2'), post-2022 publications, and IC50 values. There are 38057 full rows (1000 sampled), showing comprehensive coverage. The query matches all requested elements without unexplained LIMIT clauses. Sample stratification by publication_year ensures representative subsampling.", "score": 1.0, "decision": "YES"}
```

- 2026-02-07 09:17:45 (openrouter-free-mesh_20260207_091645; chosen: arcee-ai/trinity-large-preview:free) [log](logs/db_llm_query1_kinase_after_2022_openrouter-free-mesh_20260207_091645.log):

```sql
SELECT
    cs.canonical_smiles,
    md.chembl_id,
    td.pref_name AS target_name,
    d.year AS publication_year,
    d.doi AS article_doi,
    a.standard_value AS ic50_nM
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN docs d ON a.doc_id = d.doc_id
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.standard_type = 'IC50'
  AND a.standard_units = 'nM'
  AND d.year > 2022
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.pref_name LIKE '%kinase%';
```

Judgement J_1:
```json
{"analysis": "The SQL query correctly retrieves the requested columns (canonical_smiles, chembl_id, target_name, publication_year, article_doi, ic50_nM) for compounds with kinase inhibitor activity published after 2022. The query filters by standard_type='IC50', standard_units='nM', year>2022, and target_type='SINGLE PROTEIN' with target names containing 'kinase'. The result shows 36,737 rows from 2023, which aligns with the 2022+ filter. The data includes all required fields and appears to be correctly filtered. The sample shows diverse kinase targets with IC50 values in nM as requested. The query structure and filters are appropriate for the user's question.", "score": 1.0, "decision": "YES"}
```

2) Use my local hardware with local OSS models and OSS s/w - load models that the local h/w can run (however limited), and provide endpoints on my laptop/desktop/LAN.

```bash
RUN_LABEL="query1_kinase_after_2022_local-multi-mesh_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --multi-endpoint-profile local-mesh -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

ljubomir@macbook2(::main):~/ChEMBLdb-query$ wc -l query_results*202602*.csv
   37643 query_results_query1_kinase_after_2022_local-multi-mesh_20260207_130129.csv
   37217 query_results_query1_kinase_after_2022_local-multi-mesh_20260207_192640.csv

SQL used in those two local-mesh runs (from logs):

- 2026-02-07 13:36:50 (local-multi-mesh_20260207_130129; glm-4.7-flash on llama.cpp) [log](logs/db_llm_query1_kinase_after_2022_local-multi-mesh_20260207_130129.log):
```sql
SELECT DISTINCT
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi AS article_doi,
  a.standard_value AS ic50_value,
  a.standard_units AS ic50_units
FROM activities a
JOIN compound_structures cs ON a.molregno = cs.molregno
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN docs d ON ass.doc_id = d.doc_id
WHERE
  (td.pref_name LIKE '%kinase%' OR td.pref_name LIKE '%protein kinase%')
  AND a.standard_type = 'IC50'
  AND d.year > 2022;
```

Judgement J_2:
```json
{"analysis":"The SQL query successfully retrieved 37,642 rows of data including all requested fields: canonical_smiles, molecule_chembl_id, target_name ( kinase-related), publication_year (>2022), article_doi, and ic50_value with units. The sample shows valid data from publications in 2023-2024 with various kinase targets (e.g., JAK1, FLT3, Aurora kinases) and IC50 values in nM units.","score":0.98,"decision":"YES"}
```

- 2026-02-07 19:33:17 (local-multi-mesh_20260207_192640; glm-4.7-flash on llama.cpp) [log](logs/db_llm_query1_kinase_after_2022_local-multi-mesh_20260207_192640.log):
```sql
SELECT DISTINCT
  cs.canonical_smiles,
  md.chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi AS article_doi,
  a.standard_value AS ic50
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN docs d ON ass.doc_id = d.doc_id
WHERE td.pref_name LIKE '%kinase%'
  AND d.year > 2022
  AND a.standard_type = 'IC50'
  AND a.standard_units = 'nM'
ORDER BY a.standard_value ASC;
```

Judgement J_2:
```json
{
  "analysis": "The SQL query correctly returns a large set of rows (37216) containing the requested information: canonical_smiles, chembl_id, target_name, publication_year, article_doi, and ic50. The sample rows show that the data corresponds to kinase targets (e.g., 'Cyclin-dependent kinase 5', 'DNA-dependent protein kinase catalytic subunit') and includes valid SMILES strings, ChEMBL IDs, publication years > 2022, DOIs, and IC50 values (in nM). The query filters for 'kinase' targets, standard_type='IC50', standard_units='nM', and year > 2022, which aligns with the user's request. The query does not include a LIMIT clause, so the full result is returned (though only a sample is shown in the context). The sample rows contain some NULL values for DOI, which is expected as not all publications have DOIs. The query is well-structured and correctly joins the necessary tables to retrieve the required columns. There are no obvious issues with the query or result that would prevent it from answering the user's question truthfully and completely.",
  "score": 0.95,
  "decision": "YES"
}
```

Curently local models end points are:
- [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash) [quantised to GGUF](https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF) by [unsloth.ai](https://unsloth.ai/docs/models/glm-4.7-flash) served by llama-server by [llama.cpp](https://github.com/ggml-org/llama.cpp) built with Vulcan support on 24gb amdgpu 7900xtx.
- [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) by Qwen, served locally via [LMStudio](https://lmstudio.ai/) using [llama.cpp](https://github.com/ggml-org/llama.cpp) backend on an M2 MacBook with 96GB VRAM.

## V2 and older (V1) previous attempts

Local LLM run! Using GLM-4.7-flash released yesterday, under llama.cpp backend, and a cheapo GPU with 24 GB VRAM only. (AMD 7900xtx)
```bash
$ RUN_LABEL="query1_kinase_after_2022_glm-4.7-flash_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vvv --provider lmstudio --provider-base-url http://192.168.1.251:8081/v1 --sql-model glm-4.7-flash --judge-model glm-4.7-flash -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log
```

Got 37K+ rows returned -
```bash
$ wc -l query_results_query1_kinase_after_2022_glm-4.7-flash_20260122_013449.csv
   37204 query_results_query1_kinase_after_2022_glm-4.7-flash_20260122_013449.csv
```

In the 3rd attempt. Amusingly initially GLM-4.7-flash did not come syntactically correct SQL?? Good to see the process of recovery working.
```bash
logs/db_llm_query1_kinase_after_2022_glm-4.7-flash_20260122_013449.log
logs/intermediate/query_results_query1_kinase_after_2022_glm-4.7-flash_20260122_013449_iter3.csv
```

Ofc - all this is provisonary, I have not got a clue in anything chemistry, IDK if the rows returned make sense or the LLM SQL returns total nonsense.

The server serving the local model is
```bash
./build/bin/llama-server --device Vulkan0 --gpu-layers all --ctx-size 202752 --host 192.168.1.251 --port 8081 --model ~/llama.cpp/models/GLM-4.7-Flash-UD-Q4_K_XL.gguf --temp 1.0 --top-p 0.95 --min-p 0.01 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --jinja &
```

The LLM is [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash) [quantised to GGUF](https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF) by [unsloth.ai](https://unsloth.ai/docs/models/glm-4.7-flash).

The llama-server is by [llama.cpp](https://github.com/ggml-org/llama.cpp) built with Vulcan support:
```bash
cd ~/llama.cpp
rm -rf build
cmake . -DGGML_VULKAN=ON -B ./build
cmake --build ./build --config Release -j

Then verify your AMD GPU is detected:

./build/bin/llama-server --list-devices
```

Interesting run that on the initial fetch of 41K+ rows, the judge was unhappy:
```bash
$ RUN_LABEL="query1_kinase_after_2022_openrouter_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vvv --provider openrouter -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"
```

Can see in the log the judge disliked in iteration 1. So the SQL query got tightened in iteration 2.
```bash
logs/db_llm_query1_kinase_after_2022_openrouter_20260121_071837.log
```

The intermediate result recorded:
```bash
wc -l logs/intermediate/query_results_query1_kinase_after_2022_openrouter_20260121_071837_iter*.csv
   41399 logs/intermediate/query_results_query1_kinase_after_2022_openrouter_20260121_071837_iter1.csv
   19781 logs/intermediate/query_results_query1_kinase_after_2022_openrouter_20260121_071837_iter2.csv
```

The final result ~20K rows:
```bash
wc -l query_results_query1_kinase_after_2022_openrouter_20260121_071837.csv
   19781 query_results_query1_kinase_after_2022_openrouter_20260121_071837.csv
```

Previous canonical query run (descriptive run label + CSV output):
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

Prior run with relaxed filter + long context + CSV + logs:
```bash
unset OPENAI_API_KEY && set -a && source ./.env && set +a && RUN_LABEL="query1_kinase_after_2022_relaxed_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --provider openrouter --min-context=100000 --filter-profile relaxed --run-label "${RUN_LABEL}" -f csv -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_query1_${RUN_LABEL}.log"
```

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

Use Cerberas for speed, atm (16-Jan-2026) only big model there available is GLM-4.7:

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
$ RUN_LABEL="query1_kinase_after_2022_openai_$(date +%Y%m%d_%H%M%S)"; PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vvv --provider openai -f csv --run-label "${RUN_LABEL}" -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_${RUN_LABEL}.log"^C
```

...but only 21K+ lines of result returned - TBD debug
```bash
$ wc -l query_results_query1_kinase_after_2022_openai_20260117_170659.csv
   21339 query_results_query1_kinase_after_2022_openai_20260117_170659.csv
$ l logs/db_llm_query1_kinase_after_2022_openai_20260117_170659.log
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
$ wc -l query_results_query1_kinase_after_2022_anthropic_20260117_091522.csv
   40818 query_results_query1_kinase_after_2022_anthropic_20260117_091522.csv
$ l logs/*anthropic_20260117_091522*
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

Example session with verbose output and logging via `tee` (provider required):
```bash
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --provider llamacpp --sql-model minimax-m2.1 -q "get the smiles and chembl_id for kinase inhibitors" |& tee logs/db_llm_query_$(date +%Y%m%d_%H%M%S).log
```

```bash
RUN_LABEL=$(date +%Y%m%d_%H%M%S)
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py -vv --provider openrouter --run-label "${RUN_LABEL}" -q "get the smiles,chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" |& tee "logs/db_llm_query1_${RUN_LABEL}.log"
```

## Provider selection
Provider is required. Choose via CLI or `TEXT2SQL_PROVIDER`:
```bash
TEXT2SQL_PROVIDER=deepseek uv run python src/db_llm_query.py -q "..."
```
or
```bash
uv run python src/db_llm_query.py --provider cerebras -q "..."
```
Local llama.cpp (OpenAI-compatible) example:
```bash
LLAMACPP_BASE_URL=http://127.0.0.1:1234/v1 \
uv run python src/db_llm_query.py --provider llamacpp --sql-model minimax-m2.1 -q "..."
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

## Algorithm: Iterative Text-to-SQL with Multi-LLM Orchestration (v4)

The v4 query system uses a multi-LLM orchestration pattern inspired by open-ended search techniques. The algorithm separates concerns across three distinct LLM roles that iterate together until a satisfactory result is achieved.

### Core Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM PROMPT (SP)                             │
│  Database schema docs: tables, columns, sampled rows per table              │
│  (Cached at head, passed to all LLM calls)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER QUESTION (UQ)                                │
│  Initial natural-language query from user (provided once at start)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROMPT-WRITER LLM                                   │
│  Produces execution-oriented User Prompt (UP_1) from (SP, UQ)               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Iterative Loop (n = 1 to N)

Each iteration maintains a rolling history of the last M iterations to provide context while keeping token usage manageable.

```
Iteration n:
┌─────────────────────────────────────────────────────────────────────────────┐
│  INPUT: SP + UQ + history (last M iterations) + UP_n                        │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         SQL-WRITER LLM                                 │ │
│  │  Produces SQL_n from (SP, UQ, UP_n, history)                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│                                    ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                       EXECUTE AGAINST DB                               │ │
│  │  Run SQL_n on ChEMBL SQLite → RES_n (result table)                     │ │
│  │  Summary: plan, row count, columns, samples, errors                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│                                    ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          JUDGE LLM                                     │ │
│  │  Produces J_n from (SP, UQ, UP_n, SQL_n, PLAN_n, RES_n, history)       │ │
│  │                                                                        │ │
│  │  Returns:                                                              │ │
│  │    • Qualitative evaluation of result quality                          │ │
│  │    • Improvement advice for next iteration                             │ │
│  │    • Quantitative score [0, 1] (penultimate line)                      │ │
│  │    • Decision: YES or NO (last line)                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
                     ▼                               ▼
              YES (or score ≥ threshold)        NO (continue)
                     │                               │
                     │                               ▼
                     │               ┌──────────────────────────────┐
                     │               │    PROMPT-WRITER LLM         │
                     │               │  Produces UP_(n+1) from      │
                     │               │  (SP, UQ, full history)      │
                     │               └──────────────────────────────┘
                     │                               │
                     ▼                               ▼
            ┌───────────────────┐         ┌────────────────────┐
            │    STOP           │         │  NEXT ITERATION    │
            │  Return RES_n     │         │  (n → n+1)         │
            └───────────────────┘         └────────────────────┘
```

### History Window

The algorithm maintains a sliding window of the last M iterations to:
- Provide recent context for each LLM
- Keep token usage bounded
- Allow the system to "learn" from recent failures

History format (with clear HTML-like tags):
```
<SP>...</SP>
<UQ>...</UQ>
<ITERATION 1>
  <UP_1>...</UP_1>
  <SQL_1>...</SQL_1>
  <PLAN_1>...</PLAN_1>
  <RES_1>...</RES_1>
  <J_1>...</J_1>
</ITERATION 1>
...
<ITERATION M>
  <UP_M>...</UP_M>
  <SQL_M>...</SQL_M>
  <PLAN_M>...</PLAN_M>
  <RES_M>...</RES_M>
  <J_M>...</J_M>
</ITERATION M>
```

### Key Design Insights

1. **Separation of Concerns**: Three distinct LLM roles (prompt-writer, SQL-writer, judge) each specialize in one aspect of the problem.

2. **Explicit Feedback Loop**: The judge provides both qualitative feedback (what went wrong) and quantitative scoring (how far off are we).

3. **Bounded Context**: The M-iteration history window prevents unbounded token growth while preserving recent learning.

4. **Tagged Structure**: HTML-like tags make the flow auditable and debuggable.

### Acknowledgements

The multi-LLM orchestration pattern and iterative refinement approach were inspired by the [Poetiq ARC-AGI solver](https://github.com/poetiq-ai/poetiq-arc-agi-solver/blob/main/arc_agi/solve_coding.py), which demonstrated the effectiveness of separating generation and evaluation roles in open-ended search problems.

## CLI options (db_llm_query.py)
All options are available on `src/db_llm_query.py` (wrapper) and `src/db_llm_query_v1.py`.

Usage patterns:
```bash
uv run python src/db_llm_query.py -q "..."
echo "..." | uv run python src/db_llm_query.py
```

Options and defaults (provider required):
- `query` (positional): natural language query. Optional if provided via `-q/--query` or stdin.
- `-q, --query`: natural language query string. Default: unset.
- `--provider`: LLM provider (`auto|anthropic|openai|gemini|llamacpp|mlxlm|openrouter|deepseek|cerebras|zai|local`). Required; can also set `TEXT2SQL_PROVIDER`.
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
- `--judge-temperature`: temperature for judge model. Default: `0.5`.
