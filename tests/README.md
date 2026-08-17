# Tests

## Latest status first — April 2026

The most important current benchmark/test-like artifact is the completed full v5 judge-loop evaluation on the diversified `1010` corpus:

- split file: `experiments/case_splits_v5.1010.json`
- manifest root: `tests/v5_manifests_1010/`
- eval root: `experiments/evals/v5_forward_eval/v5_1010_full_judge_loop_20260409_101200/`
- report: `experiments/evals/v5_forward_eval/v5_1010_full_judge_loop_20260409_101200/report.json`

Current completed summary:

- total: `1010` cases
- exact pass: `350`
- pass rate: `0.346535`
- mean score: `0.787994`
- incomplete cases: `0`

The `report.json` case list now includes stable `ordinal` numbers `1..1010`, which makes case review and log cross-referencing much easier.

For v5 work, the important distinction is:

- deterministic test harnesses under `tests/` remain the authority for exact result-set comparison
- the LLM judge in the v5 loop is an iterative controller, not the final scoring authority

Relevant v5 directories:

- `tests/v5_manifests/` — earlier v5 manifests
- `tests/v5_manifests_1010/` — current diversified 1010-case manifests
- `experiments/evals/v5_forward_eval/` — v5 evaluation outputs

If you are trying to understand the current benchmark state, start from the `v5_1010_full_judge_loop_20260409_101200` report before digging into older v4-era reports below.

This directory contains deterministic, gold-standard integration tests that validate SQL output against known-good CSVs on the local ChEMBL SQLite database. These are **not** LLM calls; they execute stored SQL and compare the resulting result sets to precomputed gold CSVs.

## How to run

Run the integration suite (requires the local ChEMBL DB):
```bash
uv run pytest -m integration -q
```

Run a single case:
```bash
uv run pytest -m integration -q -k kinase_after_2022_claude
```

## Test cases (golden SQL/CSV)

The registry is in `cases/registries/archive/cases.json`. Each case points at a SQL file, a gold CSV, and the local DB path. The harness normalizes column names/values, sorts on stable keys, and compares content with float tolerance.

Tests were copy & paste scavanged from the original [Searching ChEMBL with Gemini](https://patwalters.github.io/Searching-ChEMBL-with-Gemini/) git repo.
TBD LLM tests will be added in due course. The tests below are sql &rarr; result, there is no LLM involved at all in the tests themselves.

Each run also writes:
- `*-test-result-last.csv`: the last-run result table (sorted/normalized).
- `*-metrics-last.json`: similarity metrics against the human gold baseline (thresholds + scores).

Some cases define `metric_column_map` in `cases/registries/archive/cases.json` to align semantically equivalent columns that have different names (e.g., `article_doi` vs `doi`). Only those mapped columns (plus any remaining exact-name matches) are used for the human-baseline metrics.

## LLM tests (long-running)

LLM tests are separated and marked `llm`. These do **not** execute SQL directly; instead they compare the last-run CSV result against a gold CSV.

Run the LLM job (updates the `*-test-result-last.csv` for that case):
```bash
uv run python tests/run_llm_case.py --case-id glm-4.7-flash_local
```

List all LLM cases and their commands:
```bash
uv run python tests/run_llm_case.py --list
```

By default, LLM runs are quiet (stdout suppressed) and all output goes to the case log file. Set `"quiet": false` in `cases/registries/archive/llm_cases.json` if you want live stdout.

Run LLM comparisons:
```bash
uv run pytest -m llm -q
```

The LLM cases registry lives in `cases/registries/archive/llm_cases.json` and includes the full command line, timeout, and output paths.

## FAQ high-quality cases

These cases are separate from the existing SQL goldens and the provider-specific LLM snapshots. They use the ChEMBL FAQ titles as the user questions, keep the published FAQ SQL as reference, execute a SQLite-adapted version of that SQL as ground truth, and compare that result set with the CSV from a fresh `src/db_llm_query.py` run.

Registry:
- `cases/registries/archive/faq_hq_cases.json`

Fixtures per case:
- `published.sql`: SQL copied from the GitBook FAQ page
- `sqlite.sql`: semantically equivalent SQL adapted to the local SQLite ChEMBL dump
- `result-last.csv`: last fresh LLM-run result for that FAQ case
- `ground-truth.csv`: materialized result set from the SQLite ground-truth SQL
- `ground-truth.csv.zst`: compressed copy of the materialized ground truth
- `run-last.log`: last run log for that FAQ case

List FAQ cases:
```bash
uv run python tests/run_faq_hq_case.py --list
```

Run one FAQ case with your chosen provider/model args:
```bash
uv run python tests/run_faq_hq_case.py \
  --case-id faq_sildenafil_pde5_ic50_salts \
  -- --multi-endpoint-profile zai-pony-alpha-2
```

Run all default-size FAQ cases quietly:
```bash
uv run python tests/run_faq_hq_case.py \
  --all \
  --quiet \
  -- --multi-endpoint-profile zai-pony-alpha-2
```

FAQ case logs are verbose by default: unless you pass an explicit `-v`/`-vv`/`--verbose` through to `src/db_llm_query.py`, the runner injects `-vv` so `run-last.log` includes the generated UP, SQL, result summaries, and judge text.

Run FAQ pytest checks:
```bash
uv run pytest -m faq_hq -q
```

Materialize the SQLite FAQ ground truth locally:
```bash
uv run python tests/materialize_faq_hq_ground_truth.py --all --compress
```

By default, FAQ pytest now:
- includes the `large` FAQ cases
- prefers persisted `ground-truth.csv` files when present
- falls back to `ground-truth.csv.zst` when the CSV has been removed locally

If you want to force rerunning SQL instead of using persisted ground truth:
```bash
CHEMBL_FAQ_PREFER_PERSISTED_GROUND_TRUTH=0 uv run pytest -m faq_hq -q
```

If you want to disable the `large` FAQ cases:
```bash
CHEMBL_FAQ_INCLUDE_LARGE=0 uv run pytest -m faq_hq -q
```

The PubChem FAQ case is massive and is skipped unless:
```bash
CHEMBL_FAQ_INCLUDE_MASSIVE=1 uv run pytest -m faq_hq_massive -q
```

## Web-scraped UQ/SQL pairs

The `web_scrape` fixture set stores additional `(User Question, SQL)` pairs harvested from public web sources. These are source-material fixtures first: some SQL is for older ChEMBL schemas or different SQL dialects, so they are not automatically executable tests yet.

Registry:
- `cases/registries/archive/web_scrape_cases.json`

Fixture layout:
- `tests/fixtures/web_scrape/<case_id>/uq.txt`
- `tests/fixtures/web_scrape/<case_id>/source.sql`
- `tests/fixtures/web_scrape/<case_id>/documentation.txt`
- `tests/fixtures/web_scrape/<case_id>/metadata.json`

The top-level `tests/fixtures/web_scrape/README.md` documents the corpus, and `_google_share_redirect_note.txt` records that the provided Google share link redirected into a search flow rather than exposing a stable share page for scraping.

## Web-scraped round-2 UQ/SQL pairs

The `web_scrape2` fixture set stores a second pass of `(User Question, SQL)` pairs gathered after applying lessons from the first pass:
- prefer primary-source code or documentation over search-result snippets
- preserve exact filter semantics when they are visible
- keep the second pass separate so de-duplication and promotion decisions remain auditable

Registry:
- `cases/registries/archive/web_scrape2_cases.json`

Fixture layout:
- `tests/fixtures/web_scrape2/<case_id>/uq.txt`
- `tests/fixtures/web_scrape2/<case_id>/source.sql`
- `tests/fixtures/web_scrape2/<case_id>/documentation.txt`
- `tests/fixtures/web_scrape2/<case_id>/metadata.json`

Notes:
- `tests/fixtures/web_scrape2/README.md` documents the second-pass corpus.
- `tests/fixtures/web_scrape2/_round2_notes.txt` records the round-two harvesting criteria.
- `tests/fixtures/web_scrape3/README.md` documents the third-pass corpus.
- `tests/fixtures/web_scrape3/_round3_notes.txt` records the round-three harvesting criteria.
- `tests/fixtures/web_scrape4/README.md` documents the fourth-pass corpus.
- `tests/fixtures/web_scrape4/_round4_notes.txt` records the round-four harvesting criteria.
- `tests/fixtures/web_scrape5/README.md` documents the fifth-pass corpus.
- `tests/fixtures/web_scrape5/_round5_notes.txt` records the round-five harvesting criteria.
- `tests/fixtures/web_scrape6/README.md` documents the sixth-pass corpus.
- `tests/fixtures/web_scrape6/_round6_notes.txt` records the round-six harvesting criteria.
- `tests/fixtures/web_scrape7/README.md` documents the seventh-pass corpus.
- `tests/fixtures/web_scrape7/_round7_notes.txt` records the round-seven harvesting criteria.
- `tests/fixtures/web_scrape8/README.md` documents the eighth-pass corpus.
- `tests/fixtures/web_scrape8/_round8_notes.txt` records the round-eight harvesting criteria.
- `tests/fixtures/web_scrape9/README.md` documents the ninth-pass corpus.
- `tests/fixtures/web_scrape9/_round9_notes.txt` records the round-nine harvesting criteria.
- `tests/fixtures/web_scrape10/README.md` documents the tenth-pass corpus.
- `tests/fixtures/web_scrape10/_round10_notes.txt` records the tenth-round harvesting criteria.
- `tests/fixtures/web_scrape11/README.md` documents the eleventh-pass corpus.
- `tests/fixtures/web_scrape11/_round11_notes.txt` records the eleventh-round harvesting criteria.
- `tests/fixtures/web_scrape12/README.md` documents the twelfth-pass corpus.
- `tests/fixtures/web_scrape12/_round12_notes.txt` records the twelfth-round harvesting criteria.
- `tests/fixtures/web_scrape13/README.md` documents the thirteenth-pass corpus.
- `tests/fixtures/web_scrape13/_round13_notes.txt` records the thirteenth-round harvesting criteria.
- Two stronger round-two cases have now been promoted:
  - `leelasd_approved_drugs_with_indications` into `web_scrape_hq`
  - `chembl_multitask_single_protein_nM_bioactivities` into `web_scrape_large`
- Four round-three cases have now been promoted into `web_scrape_hq`:
  - `chembl_downloader_target_pde5_single_protein_pchembl`
  - `chembl_downloader_target_dpp4_ic50_human_pchembl`
  - `chembl_downloader_document_molecules_chembl1123859`
  - `chembl_downloader_assay_chembl829152_exact`
- Three round-four public-source cases have now been promoted into `web_scrape_hq`:
  - `baoilleach_herg_bioassay_metadata`
  - `baoilleach_herg_ic50_export`
  - `leelasd_approved_drugs_with_structures`
- One narrowed executable variant has been promoted from the broad `abhik` source case:
  - `abhik_human_sub50nm_single_protein_first200`
- The remaining round-two cases are still source material only.

## Promoted web-scrape cases

A selected subset of the scraped cases has now been promoted into an executable result-comparison lane. These are the cases that were de-duplicated against the FAQ corpus, adapted to the local SQLite ChEMBL 36 schema, and found to execute cleanly.

Registry:
- `cases/registries/archive/web_scrape_hq_cases.json`
- `cases/registries/archive/web_scrape_large_cases.json`: separate large/slow promoted cases

Fixtures per promoted case:
- `source.sql`: SQL captured from the public source
- `sqlite.sql`: semantically equivalent SQL adapted to the local SQLite ChEMBL dump
- `result-last.csv`: last fresh LLM-run result for that case
- `ground-truth.csv`: materialized result set from the SQLite ground-truth SQL
- `ground-truth.csv.zst`: compressed copy of the materialized ground truth
- `run-last.log`: last run log for that case

De-duplication and promotion notes are recorded in:
- `tests/fixtures/web_scrape/_promotion_notes.txt`
- `tests/fixtures/web_scrape3/_round3_notes.txt`
- `tests/fixtures/web_scrape4/_round4_notes.txt`
- `tests/fixtures/web_scrape5/_round5_notes.txt`

List promoted web-scrape cases:
```bash
uv run python tests/run_web_scrape_case.py --list
```

Run one promoted web-scrape case:
```bash
uv run python tests/run_web_scrape_case.py \
  --case-id baoilleach_celegans_target_descriptions \
  -- --multi-endpoint-profile zai-pony-alpha-2
```

Run one promoted web-scrape case through `v4` explicitly:
```bash
uv run python tests/run_web_scrape_case.py \
  --db-llm-script src/db_llm_query_v4.py \
  --case-id chembl_downloader_target_dpp4_ic50_human_pchembl \
  -- --multi-endpoint-profile zai-glm-4.7-anthropic
```

Run all default promoted web-scrape cases quietly:
```bash
uv run python tests/run_web_scrape_case.py \
  --all \
  --quiet \
  -- --multi-endpoint-profile zai-pony-alpha-2
```

Promoted web-scrape logs are verbose by default: unless you pass an explicit `-v`/`-vv`/`--verbose` through to `src/db_llm_query.py`, the runner injects `-vv` so `run-last.log` includes the generated UP, SQL, result summaries, and judge text.

The promoted `web_scrape_hq` lane now also includes templated target-specific siblings derived from the successful HSP90 assay-organism pattern:
- `human_egfr_molecule_smiles`
- `human_jak2_molecule_smiles`
- `human_pde5_molecule_smiles`

The promoted `web_scrape_hq` lane also now includes:
- four public-source round-three target/document/assay cases from `tests/fixtures/web_scrape3`
- three public-source round-four hERG/approved-drug cases from `tests/fixtures/web_scrape4`
- three public-source round-five target-centric pChEMBL cases from `tests/fixtures/web_scrape5`
- four public-source round-six target-centric pChEMBL cases from `tests/fixtures/web_scrape6`
- three public-source round-seven exact-ID assay/document cases from `tests/fixtures/web_scrape7`
- three public-source round-eight target-centric pChEMBL cases from `tests/fixtures/web_scrape8`
- five public-source round-nine exact-ID assay/document cases from `tests/fixtures/web_scrape9`
- six public-source round-ten target-centric pChEMBL cases from `tests/fixtures/web_scrape10`
- six public-source round-eleven target-centric pChEMBL cases from `tests/fixtures/web_scrape11`
- seven public-source round-twelve exact-ID assay cases from `tests/fixtures/web_scrape12`
- seven public-source round-thirteen exact-ID document cases from `tests/fixtures/web_scrape13`
- five public-source round-fourteen target-centric pChEMBL cases from `tests/fixtures/web_scrape14`
- four public-source round-fifteen exact-ID assay cases from `tests/fixtures/web_scrape15`
- four public-source round-sixteen exact-ID document cases from `tests/fixtures/web_scrape16`
- three public-source round-seventeen exact-ID document cases from `tests/fixtures/web_scrape17`
- one narrowed executable variant derived from the broad `abhik` high-potency source case
- a total of `107` passing executable cases in the default lane

Run promoted web-scrape pytest checks:
```bash
uv run pytest -m web_scrape -q
```

Materialize the SQLite web-scrape ground truth locally:
```bash
uv run python tests/materialize_faq_hq_ground_truth.py \
  --cases cases/registries/archive/web_scrape_hq_cases.json \
  --all \
  --summary-path tests/fixtures/web_scrape/ground-truth-summary.json \
  --compress
```

By default, promoted web-scrape pytest:
- prefers persisted `ground-truth.csv` files when present
- falls back to `ground-truth.csv.zst` when the CSV has been removed locally
- excludes the separate large/slow cases

If you want to force rerunning SQL instead of using persisted ground truth:
```bash
CHEMBL_WEB_SCRAPE_PREFER_PERSISTED_GROUND_TRUTH=0 uv run pytest -m web_scrape -q
```

Run the separate large promoted case:
```bash
uv run python tests/run_web_scrape_large_case.py \
  --all \
  --quiet \
  -- --multi-endpoint-profile zai-pony-alpha-2
```

```bash
uv run pytest -m web_scrape_large -q tests/test_web_scrape_large_results.py
```

To run both integration and LLM comparisons in one go, use:
```bash
uv run pytest -m "integration or llm" -q
```

### 1) `kinase_after_2022_claude`
- **Source**: Claude SQL + CSV result (snapshot in `tests/fixtures/claude/`).
- **SQL**: `tests/fixtures/claude/query_kinase_inhibitors.sql`
- **Gold CSV**: `tests/fixtures/claude/kinase_inhibitors_after_2022.csv`
- **Intent**: Return SMILES, ChEMBL compound ID, target name, publication year, DOI, and IC50 values for kinase inhibitors published after 2022.
- **Notes**: Uses direct SQL over ChEMBL tables; no temp tables.

### 2) `kinase_after_2022_gemini`
- **Source**: Gemini recursive SQL + CSV result (snapshot in `tests/fixtures/gemini/`).
- **SQL**: `tests/fixtures/gemini/gemini_query.sql`
- **Gold CSV**: `tests/fixtures/gemini/kinase_inhibitors_after_2022.csv`
- **Intent**: Identify kinases via protein classification hierarchy (recursive CTE), then return activity rows after 2022.
- **Notes**: The SQL file includes sqlite CLI directives (`.headers`, `.mode`); the test harness strips those before execution.

### 3) `kinase_after_2022_human`
- **Source**: Human / notebook pipeline (snapshot in `tests/fixtures/human/`).
- **SQL**: `tests/fixtures/human/query_kinase_inhibitors.sql`
- **Gold CSV**: `tests/fixtures/human/kinase_inhibitors_after_2022.csv`
- **Intent**: Use a temp table of kinase target ChEMBL IDs derived from UniProt mapping, then query IC50 activities after 2022.
- **Notes**: The harness builds `tmp_ids` from:
  - `tests/fixtures/human/kinase_uniprot.csv`
  - `tests/fixtures/human/chembl_uniprot_mapping.txt`

## Normalization & comparison rules

- Column names can be lowercased.
- String values are stripped of whitespace; DOI fields are lowercased.
- Integer and float columns are cast to consistent types.
- Results are sorted on case-defined stable keys before comparison.
- Float columns use a tolerance (default `1e-6`).

These rules are implemented in `tests/helpers/chembl_asserts.py` and configured per case in `cases/registries/archive/cases.json`.
