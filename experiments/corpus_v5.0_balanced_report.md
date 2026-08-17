# Corpus v5.0 Balanced

Frozen: 2026-04-01

## What changed

The old `v4.7` corpus had 1000 cases, ~90% of which were `target_pchembl` — a single template family parameterized over different target IDs. This made the corpus fragile for prompt-pack optimization (overfit to one SQL shape) and unrepresentative of real ChEMBL query diversity.

`v5.0_balanced` was built by:

1. **Sub-sampling** `target_pchembl` from 902 to 300 (keeping best cases by uq_spec_similarity + size + diversity)
2. **Adding wave3 cases** (220 new) via backward path generation (SQL → PB_SQL → PB_UP):
   - 33 `human_target_molecule_smiles` (new target CHEMBL IDs)
   - 80 `target_ic50_pubmed_doi` (new targets with IC50 + provenance)
   - 107 `document_molecules` (new DOC publication IDs)

## Numbers

| Metric | v4.7 (old) | v5.0_balanced (new) |
|--------|-----------|-------------------|
| Total cases | 1000 | 982 |
| target_pchembl | 900 (90%) | 300 (31%) |
| document | 49 (5%) | 237 (24%) |
| assay_exact | 147 (15%) | 147 (15%) |
| target_ic50_pubmed_doi | 15 (2%) | 95 (10%) |
| human_target_mol_smiles | 6 (1%) | 73 (7%) |
| other | 12 (1%) | 76 (8%) |
| metabolism | 3 (<1%) | 30 (3%) |
| salts | 10 (1%) | 24 (2%) |

## Files

| File | Description |
|------|-------------|
| `tests/cases/web_scrape_hq_cases_v5.0_balanced.json` | Frozen snapshot (982 entries) |
| `experiments/case_splits_v5.0_balanced.json` | train=717 / val=124 / test=141 |
| `tests/cases/web_scrape_hq_cases.json` | Active registry (same 982 entries) |
| `tests/cases/web_scrape_hq_cases_archive_v4.9_target_pchembl_excluded.json` | 602 excluded target_pchembl cases |

## Generation details

- Prompt pack: `experiments/prompt_pack_v5.9.yaml`
- PB_SQL provider: Z.AI GLM-5.1 (Anthropic-compatible, with fallback to local nemotron)
- PB_UP provider: Local nemotron-cascade-2-30b-a3b on gigul2:8081
- Fixture rounds: `web_scrape_90` through `web_scrape_114`

## Validation

10-case forward sample: **7/10 pass, 3 partial** (0 chain failures)
- Mean score: 0.905
- All failures are row/column mismatches, not infrastructure errors

## Archives preserved

- Pre-rebalance 1000-case corpus: `tests/cases/web_scrape_hq_cases_v4.7.json` (if it exists in git history)
- Excluded 602 target_pchembl cases: `tests/cases/web_scrape_hq_cases_archive_v4.9_target_pchembl_excluded.json`
