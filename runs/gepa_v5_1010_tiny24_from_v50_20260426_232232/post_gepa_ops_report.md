# Post-GEPA Ops Report

- Run dir: `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232`
- Generated at: `2026-04-27T08:31:47.684246`

## Standard Questions

1. How long did the run take? `6:03.517` (363.517 s)
2. Did primary provider work? `True`
3. Was fallback used? `False`
4. Which providers were used? `{'zai-anthropic': 56}`
5. Which base URLs were used? `{'https://api.z.ai/api/anthropic': 56}`
6. Which models were used? `{'glm-4.7': 56}`
7. PF_RES success/fail counts: `{'True': 25, 'False': 3}`
8. Top PF_RES errors: `{'no such column: act.tid': 3}`
9. Prompt changed vs seed? `False`
10. Held-out test summary: `{'n_cases': 6, 'n_pass': 3, 'pass_rate': 0.5, 'mean_score': 0.916492}`

## Runtime Envelope

- Files scanned: `346`
- Start time: `2026-04-26T23:22:37.414881`
- End time: `2026-04-26T23:28:40.931850`

## Candidate Stats

- Candidate cache files: `5`
- Seed path: `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_9c2f91474af5af79.yaml`
- Best path: `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_9c2f91474af5af79.yaml`
- Seed SHA256: `9c2f91474af5af791d10475d8509e74d42adc96a22c5d4439f59de4f19d2c90c`
- Best SHA256: `9c2f91474af5af791d10475d8509e74d42adc96a22c5d4439f59de4f19d2c90c`

## Step Stats

- Step files: `84`
- Step counts: `{'res': 28, 'sql': 28, 'up': 28}`
- Phase-step counts: `{'heldout_test_res': 6, 'heldout_test_sql': 6, 'heldout_test_up': 6, 'candidate_evals_res': 22, 'candidate_evals_sql': 22, 'candidate_evals_up': 22}`
- Case error files: `0`

## PF_RES Fail Cases

- `val` `salts` `chembl3182437_ubiquitin_carboxyl_terminal_hy_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `(+/_)_tylophorine_raw264.7_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `(+/_)_tylophorine_raw264.7_ic50_salts` error=`no such column: act.tid`

## summary.json Snapshot

- Seed prompt pack: `/data1/data/ChEMBLdb-query/experiments/prompt_pack_v5.0.yaml`
- Best candidate path: `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_9c2f91474af5af79.yaml`
- Test summary: `{'n_cases': 6, 'n_pass': 3, 'pass_rate': 0.5, 'mean_score': 0.916492}`
