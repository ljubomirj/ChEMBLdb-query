SELECT
  assays.chembl_id AS assay_chembl_id,
  target_dictionary.target_type,
  target_dictionary.tax_id,
  compound_structures.canonical_smiles,
  molecule_dictionary.chembl_id AS molecule_chembl_id,
  activities.standard_type,
  activities.pchembl_value
FROM target_dictionary
JOIN assays ON target_dictionary.tid = assays.tid
JOIN activities ON assays.assay_id = activities.assay_id
JOIN molecule_dictionary ON activities.molregno = molecule_dictionary.molregno
JOIN compound_structures ON molecule_dictionary.molregno = compound_structures.molregno
WHERE target_dictionary.chembl_id = 'CHEMBL1075319'
  AND activities.standard_type = 'IC50'
  AND activities.standard_relation = '='
  AND activities.pchembl_value IS NOT NULL
ORDER BY
  molecule_chembl_id,
  assay_chembl_id,
  canonical_smiles,
  target_type,
  tax_id,
  standard_type,
  pchembl_value
LIMIT 1000
