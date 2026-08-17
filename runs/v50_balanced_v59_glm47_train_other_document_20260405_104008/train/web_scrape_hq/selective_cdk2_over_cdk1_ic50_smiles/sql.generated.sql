WITH cdk2_hits AS (
  SELECT DISTINCT act.molregno, act.standard_value AS ic50_cdk2
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary t ON a.tid = t.tid
  WHERE t.pref_name = 'CDK2'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_value < 1000
),
cdk1_hits AS (
  SELECT DISTINCT act.molregno, act.standard_value AS ic50_cdk1
  FROM activities act
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN target_dictionary t ON a.tid = t.tid
  WHERE t.pref_name = 'CDK1'
    AND act.standard_type = 'IC50'
    AND act.standard_relation = '='
    AND act.standard_value > 10000
)
SELECT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  c2.ic50_cdk2 AS ic50_target1_nM,
  c1.ic50_cdk1 AS ic50_target2_nM
FROM cdk2_hits c2
JOIN cdk1_hits c1 ON c2.molregno = c1.molregno
JOIN molecule_dictionary md ON md.molregno = c2.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
ORDER BY md.chembl_id, cs.canonical_smiles, c2.ic50_cdk2, c1.ic50_cdk1
