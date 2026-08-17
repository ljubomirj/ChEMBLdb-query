# Post-GEPA Ops Report

- Run dir: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_j4096_rb1024_fixjudge_20260429_231301`
- Generated at: `2026-04-30T02:48:52.077638`

## Standard Questions

1. How long did the run take? `50:40.728` (3040.728 s)
2. Did primary provider work? `False`
3. Was fallback used? `False`
4. Which providers were used? `{}`
5. Which base URLs were used? `{}`
6. Which models were used? `{}`
7. PF_RES success/fail counts: `{'True': 88}`
8. Top PF_RES errors: `{}`
9. Prompt changed vs seed? `False`
10. Held-out test summary: `{'n_cases': 30, 'n_pass': 14, 'pass_rate': 0.466667, 'mean_score': 0.865799}`

## Runtime Envelope

- Files scanned: `866`
- Start time: `2026-04-29T23:13:07.355960`
- End time: `2026-04-30T00:03:48.083589`

## Candidate Stats

- Candidate cache files: `3`
- Seed path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_j4096_rb1024_fixjudge_20260429_231301/candidate_cache/candidate_e03dc8dd25971d83.yaml`
- Best path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_j4096_rb1024_fixjudge_20260429_231301/candidate_cache/candidate_e03dc8dd25971d83.yaml`
- Seed SHA256: `e03dc8dd25971d83c3257f35331e155c53542d031240a5fc08161a3ff9b61ba7`
- Best SHA256: `e03dc8dd25971d83c3257f35331e155c53542d031240a5fc08161a3ff9b61ba7`

## Step Stats

- Step files: `264`
- Step counts: `{'res': 88, 'sql': 88, 'up': 88}`
- Phase-step counts: `{'candidate_evals_res': 58, 'candidate_evals_sql': 58, 'candidate_evals_up': 58, 'heldout_test_res': 30, 'heldout_test_sql': 30, 'heldout_test_up': 30}`
- Case error files: `0`

## summary.json Snapshot

- Seed prompt pack: `/opt/ljubomir/ChEMBLdb-query/experiments/prompt_pack_v5.10.yaml`
- Best candidate path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_j4096_rb1024_fixjudge_20260429_231301/candidate_cache/candidate_e03dc8dd25971d83.yaml`
- Test summary: `{'n_cases': 30, 'n_pass': 14, 'pass_rate': 0.466667, 'mean_score': 0.865799}`
