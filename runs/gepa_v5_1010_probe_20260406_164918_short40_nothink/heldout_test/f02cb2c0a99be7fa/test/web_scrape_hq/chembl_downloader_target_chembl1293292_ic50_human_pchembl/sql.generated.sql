SELECT
  a.chembl_id AS assay_chembl_id,
  td.target_type AS target_type,
  td.tax_id AS tax_id,
  cs.canonical_smiles AS canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  act.standard_type AS standard_type,
  act.pchembl_value AS pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
LEFT JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND td.chembl_id = 'CHEMBL1293292'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.tax_id = 9606
ORDER BY md.chembl_id ASC, a.chembl_id ASC
LIMIT 1000;
