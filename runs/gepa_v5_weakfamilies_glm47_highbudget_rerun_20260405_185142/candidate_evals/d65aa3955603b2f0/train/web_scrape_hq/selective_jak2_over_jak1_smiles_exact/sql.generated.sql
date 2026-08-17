WITH jak2_hits AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary td ON a.tid = td.tid
  WHERE td.chembl_id = 'CHEMBL2971'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value < 50
),
jak1_hits AS (
  SELECT DISTINCT act.molregno
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary td ON a.tid = td.tid
  WHERE td.chembl_id = 'CHEMBL2835'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
    AND act.standard_value > 200
)
SELECT
  m.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM jak2_hits j2
JOIN jak1_hits j1 ON j2.molregno = j1.molregno
JOIN molecule_dictionary m ON m.molregno = j2.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
ORDER BY m.chembl_id, cs.canonical_smiles
