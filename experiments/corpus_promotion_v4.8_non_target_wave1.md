# Corpus Promotion v4.8 Non-Target Wave 1

## Result

- Promoted staging registry into the active registry.
- Active registry: [web_scrape_hq_cases.json](/Users/ljubomir/ChEMBLdb-query/tests/cases/web_scrape_hq_cases.json)
- Snapshot registry: [web_scrape_hq_cases_v4.8.json](/Users/ljubomir/ChEMBLdb-query/tests/cases/web_scrape_hq_cases_v4.8.json)
- Source staging registry: [web_scrape_hq_cases_v4.8_non_target_wave1_staging.json](/Users/ljubomir/ChEMBLdb-query/tests/cases/web_scrape_hq_cases_v4.8_non_target_wave1_staging.json)

## Counts

- Archive count: 1000
- Active count: 1140
- Added cases: 140

Added by family:
- assay_exact: 120
- document: 20

Family counts before promotion:
- target_pchembl: 902
- assay_exact: 27
- document: 29
- salts: 10
- metabolism: 3
- other: 29

Family counts after promotion:
- target_pchembl: 902
- assay_exact: 147
- document: 49
- salts: 10
- metabolism: 3
- other: 29

## Validation gate

- Report: [report.json](/Users/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/non_target_wave1_validation_v59_retry_20260323/report.json)
- Validation result: 49 / 50 pass
- Pass rate: 0.98
- Mean score: 0.993689

Interpretation:
- Promotion is based on the retry-clean validation run, not the earlier chain-failed run.
- The only remaining miss was the known control case `approved_drugs_with_indications_and_efo`.
- The newly staged assay_exact and document additions were clean enough to promote.
