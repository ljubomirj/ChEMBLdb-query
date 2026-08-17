SELECT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE md.molregno IN (
  SELECT act1.molregno
  FROM activities act1
  JOIN assays a1 ON act1.assay_id = a1.assay_id
  JOIN target_dictionary td1 ON a1.tid = td1.tid
  WHERE td1.chembl_id = 'CHEMBL301'
    AND act1.standard_type = 'IC50'
    AND act1.standard_relation = '='
    AND act1.standard_units = 'nM'
    AND act1.standard_value < 50
)
AND md.molregno IN (
  SELECT act2.molregno
  FROM activities act2
  JOIN assays a2 ON act2.assay_id = a2.assay_id
  JOIN target_dictionary td2 ON a2.tid = td2.tid
  WHERE td2.chembl_id = 'CHEMBL4036'
    AND act2.standard_type = 'IC50'
    AND act2.standard_relation = '='
    AND act2.standard_units = 'nM'
    AND act2.standard_value > 200
)
ORDER BY 1, 2
