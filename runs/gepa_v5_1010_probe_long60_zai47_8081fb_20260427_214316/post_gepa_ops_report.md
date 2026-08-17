# Post-GEPA Ops Report

- Run dir: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_probe_long60_zai47_8081fb_20260427_214316`
- Generated at: `2026-04-27T23:12:23.479724`

## Standard Questions

1. How long did the run take? `26:34.439` (1594.439 s)
2. Did primary provider work? `True`
3. Was fallback used? `False`
4. Which providers were used? `{'zai-anthropic': 458}`
5. Which base URLs were used? `{'https://api.z.ai/api/anthropic': 458}`
6. Which models were used? `{'glm-4.7': 458}`
7. PF_RES success/fail counts: `{'False': 19, 'True': 210}`
8. Top PF_RES errors: `{'no such column: act.tid': 16, 'no such column: m.parent_molregno': 1, 'no such column: cs.canonical_smiles': 1, 'no such column: activities.tid': 1}`
9. Prompt changed vs seed? `True`
10. Held-out test summary: `{'n_cases': 30, 'n_pass': 20, 'pass_rate': 0.666667, 'mean_score': 0.856411}`

## Runtime Envelope

- Files scanned: `2759`
- Start time: `2026-04-27T21:43:21.579948`
- End time: `2026-04-27T22:09:56.018980`

## Candidate Stats

- Candidate cache files: `32`
- Seed path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_probe_long60_zai47_8081fb_20260427_214316/candidate_cache/candidate_9c2f91474af5af79.yaml`
- Best path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_probe_long60_zai47_8081fb_20260427_214316/candidate_cache/candidate_8316c7a17406c0ce.yaml`
- Seed SHA256: `9c2f91474af5af791d10475d8509e74d42adc96a22c5d4439f59de4f19d2c90c`
- Best SHA256: `8316c7a17406c0ceb98c672d1e8566ec1ff36ce56fc14196316198557f7c8642`

## Step Stats

- Step files: `687`
- Step counts: `{'res': 229, 'sql': 229, 'up': 229}`
- Phase-step counts: `{'candidate_evals_res': 199, 'candidate_evals_sql': 199, 'candidate_evals_up': 199, 'heldout_test_res': 30, 'heldout_test_sql': 30, 'heldout_test_up': 30}`
- Case error files: `0`

## PF_RES Fail Cases

- `train` `salts` `cabozantinib_met_ic50_salts` error=`no such column: act.tid`
- `train` `metabolism` `metabolism_enzyme_cyp1a2_first200` error=`no such column: m.parent_molregno`
- `val` `salts` `chembl3182437_ubiquitin_carboxyl_terminal_hy_ic50_salts` error=`no such column: act.tid`
- `val` `salts` `sorafenib_vegfr2_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `alogliptin_dpp4_ic50_salts` error=`no such column: cs.canonical_smiles`
- `train` `target_pchembl` `chembl_downloader_target_chembl1163101_ic50_human_pchembl` error=`no such column: activities.tid`
- `train` `salts` `(+/_)_tylophorine_raw264.7_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `(+/_)_tylophorine_non_protein_target_ic50_salts` error=`no such column: act.tid`
- `val` `salts` `chembl3182437_ubiquitin_carboxyl_terminal_hy_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `alogliptin_dpp4_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `cabozantinib_met_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `chembl3338195_hepg2_ic50_salts` error=`no such column: act.tid`
- `val` `salts` `sorafenib_vegfr2_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `chembl3716726_mus_musculus_ic50_salts` error=`no such column: act.tid`
- `train` `salts` `(+/_)_tylophorine_non_protein_target_ic50_salts` error=`no such column: act.tid`
- `val` `salts` `sorafenib_vegfr2_ic50_salts` error=`no such column: act.tid`
- `test` `salts` `ceritinib_alk_ic50_salts` error=`no such column: act.tid`
- `test` `salts` `chembl3183703_nacht__lrr_and_pyd_domains_con_ic50_salts` error=`no such column: act.tid`
- `test` `salts` `chembl5498743_a549_ic50_salts` error=`no such column: act.tid`

## summary.json Snapshot

- Seed prompt pack: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_9c2f91474af5af79.yaml`
- Best candidate path: `/opt/ljubomir/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_probe_long60_zai47_8081fb_20260427_214316/candidate_cache/candidate_8316c7a17406c0ce.yaml`
- Test summary: `{'n_cases': 30, 'n_pass': 20, 'pass_rate': 0.666667, 'mean_score': 0.856411}`
