WITH hits_301 AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary t ON a.tid = t.tid
  WHERE t.chembl_id = 'CHEMBL301'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value < 50
),
hits_4036 AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary t ON a.tid = t.tid
  WHERE t.chembl_id = 'CHEMBL4036'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value > 200
)
SELECT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM hits_301 h301
JOIN hits_4036 h4036 ON h301.molregno = h4036.molregno
JOIN molecule_dictionary md ON md.molregno = h301.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
ORDER BY md.chembl_id, cs.canonical_smiles
