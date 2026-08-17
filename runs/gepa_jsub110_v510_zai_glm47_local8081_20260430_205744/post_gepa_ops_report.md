# Post-GEPA Ops Report

- Run dir: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_zai_glm47_local8081_20260430_205744`
- Generated at: `2026-04-30T23:06:08.289133`

## Standard Questions

1. How long did the run take? `50:52.819` (3052.819 s)
2. Did primary provider work? `False`
3. Was fallback used? `False`
4. Which providers were used? `{}`
5. Which base URLs were used? `{}`
6. Which models were used? `{}`
7. PF_RES success/fail counts: `{'True': 96}`
8. Top PF_RES errors: `{}`
9. Prompt changed vs seed? `False`
10. Held-out test summary: `{'n_cases': 30, 'n_pass': 13, 'pass_rate': 0.433333, 'mean_score': 0.863497}`

## Runtime Envelope

- Files scanned: `935`
- Start time: `2026-04-30T20:58:05.603455`
- End time: `2026-04-30T21:48:58.422142`

## Candidate Stats

- Candidate cache files: `2`
- Seed path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_zai_glm47_local8081_20260430_205744/candidate_cache/candidate_e03dc8dd25971d83.yaml`
- Best path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_zai_glm47_local8081_20260430_205744/candidate_cache/candidate_e03dc8dd25971d83.yaml`
- Seed SHA256: `e03dc8dd25971d83c3257f35331e155c53542d031240a5fc08161a3ff9b61ba7`
- Best SHA256: `e03dc8dd25971d83c3257f35331e155c53542d031240a5fc08161a3ff9b61ba7`

## Step Stats

- Step files: `288`
- Step counts: `{'res': 96, 'sql': 96, 'up': 96}`
- Phase-step counts: `{'candidate_evals_res': 66, 'candidate_evals_sql': 66, 'candidate_evals_up': 66, 'heldout_test_res': 30, 'heldout_test_sql': 30, 'heldout_test_up': 30}`
- Case error files: `3`

## summary.json Snapshot

- Seed prompt pack: `/opt/ljubomir/ChEMBLdb-query/experiments/prompt_pack_v5.10.yaml`
- Best candidate path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_jsub110_v510_zai_glm47_local8081_20260430_205744/candidate_cache/candidate_e03dc8dd25971d83.yaml`
- Test summary: `{'n_cases': 30, 'n_pass': 13, 'pass_rate': 0.433333, 'mean_score': 0.863497}`
