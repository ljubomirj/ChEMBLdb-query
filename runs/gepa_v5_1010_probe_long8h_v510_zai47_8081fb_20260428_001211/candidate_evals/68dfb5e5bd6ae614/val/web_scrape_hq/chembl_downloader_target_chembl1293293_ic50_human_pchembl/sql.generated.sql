SELECT
  assays.chembl_id AS assay_chembl_id,
  target_dictionary.target_type,
  target_dictionary.tax_id,
  compound_structures.canonical_smiles,
  molecule_dictionary.chembl_id AS molecule_chembl_id,
  activities.standard_type,
  activities.pchembl_value
FROM activities
INNER JOIN assays ON activities.assay_id = assays.assay_id
INNER JOIN target_dictionary ON target_dictionary.tid = assays.tid
INNER JOIN molecule_dictionary ON activities.molregno = molecule_dictionary.molregno
INNER JOIN compound_structures ON activities.molregno = compound_structures.molregno
WHERE target_dictionary.chembl_id = 'CHEMBL1293293'
  AND activities.standard_type = 'IC50'
  AND activities.standard_relation = '='
  AND activities.pchembl_value IS NOT NULL
ORDER BY molecule_dictionary.chembl_id, assays.chembl_id
LIMIT 1000
