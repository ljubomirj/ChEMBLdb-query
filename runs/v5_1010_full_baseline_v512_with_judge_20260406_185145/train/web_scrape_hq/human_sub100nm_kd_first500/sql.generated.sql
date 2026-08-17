SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles, a.standard_type, a.standard_value, a.standard_units
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_records cr ON a.record_id = cr.record_id
JOIN molecule_dictionary m ON cr.molregno = m.molregno
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE a.bao_endpoint = 'Kd'
  AND a.standard_type = 'Kd'
  AND a.standard_relation = '='
  AND a.standard_value < 100
  AND a.standard_units = 'nM'
  AND a.standard_flag = 1
  AND a.potential_duplicate = 0
  AND a.standard_type IS NOT NULL
  AND a.standard_value IS NOT NULL
  AND a.standard_units IS NOT NULL
  AND a.standard_relation IS NOT NULL
  AND ass.assay_type = 'B'
  AND ass.assay_organism = 'Homo sapiens'
  AND td.target_type = 'SINGLE PROTEIN'
LIMIT 500;
