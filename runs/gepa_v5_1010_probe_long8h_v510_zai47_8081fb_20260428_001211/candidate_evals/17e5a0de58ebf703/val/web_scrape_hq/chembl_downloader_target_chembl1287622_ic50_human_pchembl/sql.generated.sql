SELECT
  assays.chembl_id AS assay_chembl_id,
  td.target_type,
  td.tax_id,
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  act.standard_type,
  act.pchembl_value
FROM activities act
INNER JOIN assays ON act.assay_id = assays.assay_id
INNER JOIN target_dictionary td ON td.tid = assays.tid
INNER JOIN molecule_dictionary md ON act.molregno = md.molregno
INNER JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE
  td.chembl_id = 'CHEMBL1287622'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.tax_id = 9606
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
ORDER BY
  molecule_chembl_id ASC,
  assay_chembl_id ASC
LIMIT 1000
