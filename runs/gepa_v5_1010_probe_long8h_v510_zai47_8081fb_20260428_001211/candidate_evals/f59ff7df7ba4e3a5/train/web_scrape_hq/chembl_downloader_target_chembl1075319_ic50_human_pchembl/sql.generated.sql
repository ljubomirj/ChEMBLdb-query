SELECT
  assays.chembl_id AS assay_chembl_id,
  target_dictionary.target_type,
  target_dictionary.tax_id,
  compound_structures.canonical_smiles,
  molecule_dictionary.chembl_id AS molecule_chembl_id,
  activities.standard_type,
  activities.pchembl_value
FROM activities
JOIN assays ON activities.assay_id = assays.assay_id
JOIN target_dictionary ON assays.tid = target_dictionary.tid
JOIN molecule_dictionary ON activities.molregno = molecule_dictionary.molregno
JOIN compound_structures ON activities.molregno = compound_structures.molregno
WHERE
  target_dictionary.chembl_id = 'CHEMBL1075319'
  AND activities.standard_type = 'IC50'
  AND activities.standard_relation = '='
  AND activities.pchembl_value IS NOT NULL
ORDER BY
  molecule_chembl_id ASC,
  assay_chembl_id ASC
LIMIT 1000
