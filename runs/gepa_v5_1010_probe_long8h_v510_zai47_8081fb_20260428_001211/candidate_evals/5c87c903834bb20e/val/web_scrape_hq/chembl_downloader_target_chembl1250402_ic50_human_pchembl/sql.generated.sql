SELECT
  assays.chembl_id AS assay_chembl_id,
  td.target_type,
  td.tax_id,
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  activities.standard_type,
  activities.pchembl_value
FROM activities
JOIN assays ON activities.assay_id = assays.assay_id
JOIN target_dictionary td ON assays.tid = td.tid
JOIN molecule_dictionary md ON activities.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE
  td.chembl_id = 'CHEMBL1250402'
  AND activities.standard_type = 'IC50'
  AND activities.standard_relation = '='
  AND activities.pchembl_value IS NOT NULL
ORDER BY
  molecule_chembl_id ASC,
  assay_chembl_id ASC
LIMIT 1000
