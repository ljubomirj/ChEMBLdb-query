WITH hits_203 AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  WHERE a.tid = (SELECT tid FROM target_dictionary WHERE chembl_id = 'CHEMBL203')
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value < 50
),
hits_1824 AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  WHERE a.tid = (SELECT tid FROM target_dictionary WHERE chembl_id = 'CHEMBL1824')
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value > 200
)
SELECT
  m.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM hits_203 h203
JOIN hits_1824 h1824 ON h203.molregno = h1824.molregno
JOIN molecule_dictionary m ON h203.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
ORDER BY m.chembl_id, cs.canonical_smiles
