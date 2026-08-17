# Case Expansion Queue v4.1

This queue enumerates the next benchmark-expansion wave after promoting the two strongest `web_scrape2` cases. The goal is to add family-balanced executable cases rather than more isolated examples.

## Newly promoted now

1. `leelasd_approved_drugs_with_indications`
- Lane: `web_scrape_hq`
- Family: drug indication / approved drugs
- Template value: good medium-sized multi-table result set with exact output columns

2. `chembl_multitask_single_protein_nM_bioactivities`
- Lane: `web_scrape_large`
- Family: target-centric potency
- Template value: strong large-case benchmark for filter semantics and schema fidelity

## Next templated cases

1. `human_egfr_molecule_smiles`
- Family: target-centric potency
- Template from: `baoilleach_human_hsp90_molecule_smiles`
- Replace target with `CHEMBL203` / EGFR
- Expected lane: `web_scrape_hq`
- Status: implemented

2. `human_jak2_molecule_smiles`
- Family: target-centric potency
- Template from: `baoilleach_human_hsp90_molecule_smiles`
- Replace target with `CHEMBL2971` / JAK2
- Expected lane: `web_scrape_hq`
- Status: implemented

3. `human_pde5_molecule_smiles`
- Family: target-centric potency
- Template from: `baoilleach_human_hsp90_molecule_smiles`
- Replace target with `CHEMBL1827` / PDE5A
- Expected lane: `web_scrape_hq`
- Status: implemented

3a. `human_erbb2_molecule_smiles`
- Family: target-centric potency
- Template from: `baoilleach_human_hsp90_molecule_smiles`
- Replace target with `CHEMBL1824` / ERBB2
- Expected lane: `web_scrape_hq`
- Status: implemented

3b. `human_kit_molecule_smiles`
- Family: target-centric potency
- Template from: `baoilleach_human_hsp90_molecule_smiles`
- Replace target with `CHEMBL1936` / KIT
- Expected lane: `web_scrape_hq`
- Status: implemented

3c. `human_dpp4_molecule_smiles`
- Family: target-centric potency
- Template from: `baoilleach_human_hsp90_molecule_smiles`
- Replace target with `CHEMBL284` / DPP4
- Expected lane: `web_scrape_hq`
- Status: implemented

4. `approved_drugs_with_mechanisms`
- Family: drug mechanism / approved drugs
- Template from: `leelasd_approved_drugs_with_indications`
- Extend with `drug_mechanism`
- Expected lane: `web_scrape_hq`
- Status: implemented

5. `approved_drugs_with_indications_phase4_only`
- Family: drug indication / approved drugs
- Template from: `leelasd_approved_drugs_with_indications`
- Keep the same base query but tighten expected output wording and column names
- Expected lane: `web_scrape_hq`

6. `approved_drugs_with_indications_and_efo`
- Family: drug indication / approved drugs
- Template from: `chembl_downloader_drug_indications`
- Restrict to `max_phase_for_ind = 4`
- Expected lane: `web_scrape_hq`
- Status: implemented

7. `parent_salt_ic50_atorvastatin_single_target`
- Family: compound and salts
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Substitute a different parent/salt family with shared target activities
- Expected lane: `faq_hq`-style or a promoted salts lane

8. `parent_salt_ic50_imatinib_single_target`
- Family: compound and salts
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Same skeleton, different parent/salt family
- Expected lane: `faq_hq`-style or a promoted salts lane
- Status: implemented as `imatinib_kit_ic50_salts`

8a. `sitagliptin_dpp4_ic50_salts`
- Family: compound and salts
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Same skeleton, different parent/salt family
- Expected lane: `web_scrape_hq`
- Status: implemented

9. `metabolism_first200_parent_names`
- Family: metabolism
- Template from: `iwatobipen_metabolism_example`
- Variant on a nearby metabolism projection that still fits in a small result set
- Expected lane: `web_scrape_hq`
- Status: implemented

10. `metabolism_first200_with_record_keys`
- Family: metabolism
- Template from: `iwatobipen_metabolism_example`
- Add stable identifiers to increase schema difficulty
- Expected lane: `web_scrape_hq`
- Status: implemented

11. `all_single_protein_targets_accession_sequence`
- Family: target metadata
- Template from: `faq_all_protein_targets`
- Narrow from all protein parent types to `SINGLE PROTEIN`
- Expected lane: `faq_hq` or promoted metadata lane
- Status: implemented

12. `human_single_protein_targets_accession_sequence`
- Family: target metadata
- Template from: `faq_all_protein_targets`
- Add `organism = 'Homo sapiens'`
- Expected lane: `faq_hq` or promoted metadata lane
- Status: implemented

13. `selective_cdk2_over_cdk5_smiles_exact`
- Family: selectivity
- Template from: `faq_cdk2_selective_over_cdk5`
- Make the UQ explicit about exact target names and exact output columns
- Expected lane: `faq_hq`
- Status: implemented in `web_scrape_hq`

14. `selective_cox2_over_cox1_smiles_exact`
- Family: selectivity
- Template from: the broad COX selectivity pattern surfaced during failed FAQ optimization
- Constrain the targets and output schema explicitly
- Expected lane: `faq_hq` or a promoted selectivity lane

14a. `selective_egfr_over_erbb2_smiles_exact`
- Family: selectivity
- Template from: `faq_cdk2_selective_over_cdk5`
- Make the UQ explicit about exact target names and exact output columns
- Expected lane: `web_scrape_hq`
- Status: implemented

14b. `selective_jak2_over_jak1_smiles_exact`
- Family: selectivity
- Template from: `faq_cdk2_selective_over_cdk5`
- Make the UQ explicit about exact target names and exact output columns
- Expected lane: `web_scrape_hq`
- Status: implemented

15. `target_ic50_with_pubmed_or_doi_egfr`
- Family: publication/document joins
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Keep the document join and required provenance columns, swap the target family
- Expected lane: `faq_hq`
- Status: implemented

16. `target_ic50_with_pubmed_or_doi_jak2`
- Family: publication/document joins
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Same document-centric output shape, different target
- Expected lane: `faq_hq`
- Status: implemented

16a. `target_ic50_with_pubmed_or_doi_erbb2`
- Family: publication/document joins
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Same document-centric output shape, different target
- Expected lane: `web_scrape_hq`
- Status: implemented

16b. `target_ic50_with_pubmed_or_doi_kit`
- Family: publication/document joins
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Same document-centric output shape, different target
- Expected lane: `web_scrape_hq`
- Status: implemented

16c. `target_ic50_with_pubmed_or_doi_dpp4`
- Family: publication/document joins
- Template from: `faq_sildenafil_pde5_ic50_salts`
- Same document-centric output shape, different target
- Expected lane: `web_scrape_hq`
- Status: implemented

## Promotion order

1. Add the three target-centric HSP90 siblings.
2. Add the two approved-drug indication/mechanism siblings.
3. Add the two metabolism variants.
4. Add the two target-metadata variants.
5. Add the two publication/document variants.
6. Add the explicit selectivity cases only after their UQs are nailed down.
7. COX selectivity remains deferred because the current ChEMBL 36 SQLite data yields an empty result set for the strict `IC50 < 50` vs `> 200` pattern.

## Split guidance

- Keep large cases out of the inner optimization loop by default.
- Do not update `experiments/case_splits_v4.0.json`; create a new split file after the next 8-12 executable cases are added.
