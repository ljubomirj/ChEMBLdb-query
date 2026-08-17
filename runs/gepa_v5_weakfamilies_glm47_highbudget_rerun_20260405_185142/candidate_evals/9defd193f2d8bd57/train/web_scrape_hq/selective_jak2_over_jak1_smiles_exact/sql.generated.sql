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
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN jak2_hits j2 ON md.molregno = j2.molregno
JOIN jak1_hits j1 ON md.molregno = j1.molregno
ORDER BY md.chembl_id, cs.canonical_smiles
