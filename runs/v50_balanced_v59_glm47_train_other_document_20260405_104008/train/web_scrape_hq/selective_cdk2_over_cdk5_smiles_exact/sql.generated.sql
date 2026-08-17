WITH cdk2_hits AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary td ON a.tid = td.tid
  WHERE td.chembl_id = 'CHEMBL301'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value < 50
),
cdk5_hits AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary td ON a.tid = td.tid
  WHERE td.chembl_id = 'CHEMBL4036'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value > 200
)
SELECT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN cdk2_hits h2 ON h2.molregno = md.molregno
JOIN cdk5_hits h5 ON h5.molregno = md.molregno
ORDER BY md.chembl_id, cs.canonical_smiles
