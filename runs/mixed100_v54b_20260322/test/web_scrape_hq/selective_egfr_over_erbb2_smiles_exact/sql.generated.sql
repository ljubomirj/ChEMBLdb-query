SELECT DISTINCT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN activities a ON a.molregno = md.molregno
JOIN assays ass ON ass.assay_id = a.assay_id
JOIN target_dictionary td ON td.tid = ass.tid
WHERE a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_units = 'nM'
  AND a.standard_value IS NOT NULL
  AND (
    (td.chembl_id = 'CHEMBL203' AND a.standard_value < 50)
    OR
    (td.chembl_id = 'CHEMBL1824' AND a.standard_value > 200)
  )
  AND EXISTS (
    SELECT 1
    FROM activities a1
    JOIN assays ass1 ON ass1.assay_id = a1.assay_id
    JOIN target_dictionary td1 ON td1.tid = ass1.tid
    WHERE a1.molregno = md.molregno
      AND a1.standard_type = 'IC50'
      AND a1.standard_relation = '='
      AND a1.standard_units = 'nM'
      AND a1.standard_value IS NOT NULL
      AND td1.chembl_id = 'CHEMBL203'
      AND a1.standard_value < 50
  )
  AND EXISTS (
    SELECT 1
    FROM activities a2
    JOIN assays ass2 ON ass2.assay_id = a2.assay_id
    JOIN target_dictionary td2 ON td2.tid = ass2.tid
    WHERE a2.molregno = md.molregno
      AND a2.standard_type = 'IC50'
      AND a2.standard_relation = '='
      AND a2.standard_units = 'nM'
      AND a2.standard_value IS NOT NULL
      AND td2.chembl_id = 'CHEMBL1824'
      AND a2.standard_value > 200
  )
ORDER BY md.chembl_id, cs.canonical_smiles;
