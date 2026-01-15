# Agent Guide: Text2ChEMBL (Outer Loop)

This guide is for agents (Codex / Claude Code / OpenCode) orchestrating the outer loop around `src/db_llm_query_v1.py`.

## Quick Start

1) Ensure the SQLite DB exists:
- Default path: `database/latest/chembl_36/chembl_36_sqlite/chembl_36.db`
- If it lives elsewhere, pass `--db-path /path/to/chembl_36.db`
- If only the archive is present, extract it:
  - `tar -xzf database/latest/chembl_36_sqlite.tar.gz -C database/latest`

2) Run a query:
```
python src/db_llm_query_v1.py "find the smiles and chembl_id for EGFR inhibitors with IC50 < 100 nM"
```

3) First run will auto-generate schema docs at:
- `doc/chembl_database_schema.md`

## Inner Loop Behavior

The script maintains a strict loop:
- Prompt-writer -> SQL-writer -> SQLite execution -> Judge -> Prompt refinement
- It stops on `YES` or when score >= threshold.

Use `-vv` to see UP/SQL/RES/J blocks and debug iterations.

## Recommended Prompting (UQ / UP)

For best results, be explicit about:
- Target definition (species, target_type, protein family)
- Bioactivity type (`IC50`, `Ki`, `EC50`, etc.)
- Units (`nM`, `uM`)
- Required output columns (e.g., `canonical_smiles`, `molecule_chembl_id`, `assay_id`, `target_name`, `doc_id`, `year`)
- Filters (date ranges, confidence_score, assay_type)

## Common Join Patterns (ChEMBL)

Useful tables often include:
- `activities`, `assays`, `target_dictionary`, `target_components`
- `molecule_dictionary`, `compound_structures`
- `docs`, `compound_records`

If results look incomplete, check:
- Target classification hierarchy (`protein_classification`) vs. UniProt lists
- Assay type and confidence score filters
- Units and standard_type alignment

## Operational Tips

- Large outputs: ask for `LIMIT` or add a date range.
- If the judge says results are empty, refine the target constraints or relax filters.
- If you need full exports, run with `-a` or `--format csv` to save results.

