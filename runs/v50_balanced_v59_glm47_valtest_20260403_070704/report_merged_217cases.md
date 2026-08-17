# v5 Forward Eval Merged Report

- Eval root: `experiments/evals/v5_forward_eval/v50_balanced_v59_glm47_valtest_20260403_070704`
- Prompt pack: `experiments/prompt_pack_v5.9.yaml`
- Split file: `experiments/case_splits_v5.0_balanced.json`
- Aggregated from: `217` unique case artifacts
- Split entries in file: `219`; unique `(split, corpus, case_id)` items: `217`

## Summary

- Cases: `217`
- Pass: `167`
- Partial: `49`
- Fail: `1`
- Pass rate: `0.769585`
- Mean score: `0.950473`
- Case errors: `0`

## By Split

- `test`: n=111, pass=86, partial=24, fail=1, pass_rate=0.774775, mean_score=0.954063
- `val`: n=106, pass=81, partial=25, fail=0, pass_rate=0.764151, mean_score=0.946713

## By Family

- `assay_exact`: n=45, pass=45, partial=0, fail=0, pass_rate=1.0, mean_score=1.0
- `document`: n=39, pass=23, partial=16, fail=0, pass_rate=0.589744, mean_score=0.938462
- `metabolism`: n=6, pass=2, partial=4, fail=0, pass_rate=0.333333, mean_score=0.9
- `other`: n=42, pass=14, partial=28, fail=0, pass_rate=0.333333, mean_score=0.842919
- `salts`: n=11, pass=9, partial=1, fail=1, pass_rate=0.818182, mean_score=0.895455
- `target_pchembl`: n=74, pass=74, partial=0, fail=0, pass_rate=1.0, mean_score=1.0

## Duplicate Split Entries

- `test` / `web_scrape_hq` / `target_ic50_with_pubmed_or_doi_amine_oxidase_flavin_containing_a` appears `2` times in the split file
- `test` / `web_scrape_hq` / `target_ic50_with_pubmed_or_doi_amine_oxidase_flavin_containing_b` appears `2` times in the split file

## Worst Cases

- `test` / `salts` / `chembl3183703_nacht__lrr_and_pyd_domains_con_ic50_salts`: status=fail, score=0.0
- `val` / `other` / `human_adenosine_receptor_a2a_molecule_smiles`: status=partial, score=0.6
- `val` / `other` / `target_ic50_with_pubmed_or_doi_histone_deacetylase_6`: status=partial, score=0.6
- `val` / `other` / `target_ic50_with_pubmed_or_doi_serine_threonine_protein_kinase_pim_1`: status=partial, score=0.6
- `val` / `other` / `target_ic50_with_pubmed_or_doi_tyrosine_protein_kinase_jak2`: status=partial, score=0.6
- `val` / `other` / `target_ic50_with_pubmed_or_doi_sodium_dependent_dopamine_transporter`: status=partial, score=0.608521
- `test` / `other` / `target_ic50_with_pubmed_or_doi_prostaglandin_g_h_synthase_2`: status=partial, score=0.608689
- `test` / `other` / `approved_drugs_indication_multiple_myeloma`: status=partial, score=0.643373
- `val` / `other` / `target_ic50_with_pubmed_or_doi_hepatocyte_growth_factor_receptor`: status=partial, score=0.643891
- `val` / `other` / `target_ic50_with_pubmed_or_doi_isocitrate_dehydrogenase_nadp_cytoplasmic`: status=partial, score=0.64676
- `val` / `other` / `approved_drugs_indication_chronic_kidney_disease`: status=partial, score=0.690141
- `val` / `other` / `target_ic50_with_pubmed_or_doi_rac_alpha_serine_threonine_protein_kinase`: status=partial, score=0.762253
- `test` / `other` / `approved_drugs_indication_hypertension`: status=partial, score=0.798953
- `test` / `document` / `chembl_downloader_document_molecules_chembl1135903`: status=partial, score=0.85
- `test` / `document` / `chembl_downloader_document_molecules_chembl1136837`: status=partial, score=0.85
