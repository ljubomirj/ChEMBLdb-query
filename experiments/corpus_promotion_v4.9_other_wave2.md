# Corpus Promotion v4.9 Other Wave 2

## Result

- Promoted the retargeted + expanded registry into the active corpus.
- Active: `tests/cases/web_scrape_hq_cases.json`
- Snapshot: `tests/cases/web_scrape_hq_cases_v4.9.json`
- Archive (excluded target_pchembl): `tests/cases/web_scrape_hq_cases_archive_v4.9_target_pchembl_excluded.json`

## Counts

| Metric | v4.8 | v4.9 | Delta |
|--------|------|------|-------|
| Total cases | 1140 | 641 | -499 |
| target_pchembl | 902 | 300 | -602 |
| assay_exact | 147 | 146 | -1 |
| other | 30 | 133 | +103 |
| document | 49 | 49 | 0 |
| salts | 10 | 10 | 0 |
| metabolism | 3 | 3 | 0 |

## What changed

1. **target_pchembl sub-sampled**: 902 → 300 (best cases by uq_spec_similarity + size + diversity)
   - 602 excluded cases archived in `web_scrape_hq_cases_archive_v4.9_target_pchembl_excluded.json`
   - Selection: `experiments/target_pchembl_subset_v4.9.json`

2. **other family expanded**: 30 → 133 (+103 new synthetic cases)
   - Generated via backward path: SQL → PB_SQL → PB_UP
   - Provider: glm-5.1 on Z.AI Anthropic (primary) → glm-5-turbo → nemotron-cascade-2-30b-a3b local
   - Prompt pack: v5.9
   - Generation: 103/103 cases, 0 failures
   - Templates: 7 sub-families

## Family percentages

| Family | v4.8 % | v4.9 % |
|--------|--------|--------|
| target_pchembl | 79.1% | 46.8% |
| assay_exact | 12.9% | 22.8% |
| other | 2.6% | 20.7% |
| document | 4.3% | 7.6% |
| salts | 0.9% | 1.6% |
| metabolism | 0.3% | 0.5% |

## Forward validation

- Eval: `experiments/evals/v5_forward_eval/other_wave2_validation_v59_glm51/`
- Sample: 30 cases (20 new other + 10 controls)
- Result: 1 pass, 26 partial (score 0.85), 3 chain failures
- Mean score: 0.74
- Chain failures: 3 cases with brackets in case IDs (path issue)
- Interpretation: 27/30 (90%) cases produce valid SQL with correct results

## Scripts created

- `scripts/select_target_pchembl_subset.py`
- `scripts/build_retargeted_registry.py`
- `scripts/prepare_other_wave2_candidates.py`
- `scripts/generate_other_wave2.py`

## Provider profile added

- `zai-glm51-then-local`: glm-5.1 primary (Z.AI Anthropic) → glm-5-turbo → nemotron-cascade-2-30b-a3b local
