# Target pChEMBL Subset Selection v4.9

- Total target_pchembl cases: 902
- Selected: 300
- Excluded: 602

## Scoring

`final_score = 0.5 * norm(uq_spec_similarity) + 0.3 * size_score + 0.2 * diversity_bonus`

- `norm(uq_spec_similarity)`: percentile rank within 902
- `size_score`: prefer 50-5000 result rows
- `diversity_bonus`: cap 3 per target name, then 0.5 for ranks 4-5, 0 for 6+

## Selected cases summary

- Mean uq_spec_similarity: 0.3533
- Median uq_spec_similarity: 0.3476
- Mean row count: 545
- Median row count: 404
- Unique target names: 299

## Excluded cases summary

- Mean uq_spec_similarity: 0.3109
- Median uq_spec_similarity: 0.3146

## Score distribution (selected)

| Metric | Min | Max | Mean |
|--------|-----|-----|------|
| uq_spec_similarity | 0.3278 | 0.5270 | 0.3533 |
| final_score | 0.7420 | 1.0000 | 0.8619 |
