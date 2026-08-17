SELECT
  a.chembl_id AS assay_chembl_id,
  t.target_type,
  t.tax_id,
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  act.standard_type,
  act.pchembl_value
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN activities act ON md.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
WHERE t.chembl_id = 'CHEMBL2034'
  AND t.target_type = 'SINGLE PROTEIN'
  AND t.tax_id = 9606
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
ORDER BY md.chembl_id, a.chembl_id
LIMIT 1000
