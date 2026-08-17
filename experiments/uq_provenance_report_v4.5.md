# UQ Provenance Report v4.5

## AKT1 case genesis

- Case: `chembl_downloader_target_akt1_ic50_human_pchembl`
- Fixture: `tests/fixtures/web_scrape14/chembl_downloader_target_akt1_ic50_human_pchembl`
- Source family: `chembl_downloader.get_target_sql`
- Generator lineage: early hand-written templated target rounds, later formalized by `scripts/generate_expansion_rounds.py:create_target_case()`.
- Metadata marks these UQs as parameter-derived rather than scraped from real user wording.

## What was actually scraped

- The repo harvested public SQL/query-function patterns from `chembl_downloader`.
- It did not harvest a natural user question for this family.
- The old verbose UQ text was generated locally from target ID, target name, projected columns, and SQL filters.

## Current policy

- `uq.txt` now stores a more human-like request for the target-pChEMBL family.
- `benchmark_spec_uq.txt` preserves the old executable-spec wording.
- Case metadata records `uq_style = realistic_uq` and `uq_origin_kind = templated_from_sql`.

## Split proposal

- realistic_uq: 141 cases
- executable_spec_uq: 59 cases
- synthetic_origin_realistic_uq: 102 cases

Use the binary split for benchmark reporting, and the synthetic-origin subset when you want to track cases whose surface wording is realistic but whose provenance is still templated SQL.
