SELECT
  assays.chembl_id AS assay_chembl_id,
  target_dictionary.target_type,
  target_dictionary.tax_id,
  compound_structures.canonical_smiles,
  molecule_dictionary.chembl_id AS molecule_chembl_id,
  activities.standard_type,
  activities.pchembl_value
FROM activities
JOIN assays ON assays.assay_id = activities.assay_id
JOIN target_dictionary ON target_dictionary.tid = assays.tid
JOIN molecule_dictionary ON molecule_dictionary.molregno = activities.molregno
JOIN compound_structures ON compound_structures.molregno = molecule_dictionary.molregno
WHERE
  activities.standard_type = 'IC50'
  AND activities.standard_relation = '='
  AND activities.pchembl_value IS NOT NULL
  AND target_dictionary.chembl_id = 'CHEMBL1075319'
  AND target_dictionary.tax_id = 9606
ORDER BY
  molecule_chembl_id,
  assay_chembl_id
LIMIT 1000
