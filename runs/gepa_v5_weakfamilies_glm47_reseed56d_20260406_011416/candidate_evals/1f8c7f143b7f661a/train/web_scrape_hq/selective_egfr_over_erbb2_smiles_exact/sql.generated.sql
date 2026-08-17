WITH egfr_activities AS (
  SELECT
    act.molregno,
    MIN(act.standard_value) AS min_ic50_egfr
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary td ON a.tid = td.tid
  WHERE td.chembl_id = 'CHEMBL203'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
  GROUP BY act.molregno
  HAVING MIN(act.standard_value) < 50
),
erbb2_activities AS (
  SELECT
    act.molregno,
    MIN(act.standard_value) AS min_ic50_erbb2
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary td ON a.tid = td.tid
  WHERE td.chembl_id = 'CHEMBL1824'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_units = 'nM'
  GROUP BY act.molregno
  HAVING MIN(act.standard_value) > 200
)
SELECT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM egfr_activities e
JOIN erbb2_activities er ON e.molregno = er.molregno
JOIN molecule_dictionary md ON e.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
ORDER BY md.chembl_id, cs.canonical_smiles
