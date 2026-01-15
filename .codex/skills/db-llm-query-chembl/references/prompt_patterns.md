# Prompt Patterns

These templates help steer the LLM toward correct joins and columns.

## Column-explicit template

"Return the following columns only: molecule ChEMBL ID, target ChEMBL ID, target name, canonical SMILES, standard_type, standard_value, standard_units, pchembl_value, assay_description, document year, document DOI. Filter to single-protein targets. IC50 only, units nM, year >= 2022."

## Relationship template

"Join molecule -> activities -> assays -> targets -> documents. Use standard activity fields and document metadata."

## Unit/measurement template

"Use standard_type = 'IC50' and standard_units = 'nM'. Prefer standard_value and pchembl_value."

## Target-class template

"Filter target class to kinases; single-protein targets only."

## Publication filter template

"Only rows with document year >= 2022 and DOI present."

## If results are too sparse

"Relax to confidence >= 8, allow missing DOI, keep IC50 and year >= 2022."
