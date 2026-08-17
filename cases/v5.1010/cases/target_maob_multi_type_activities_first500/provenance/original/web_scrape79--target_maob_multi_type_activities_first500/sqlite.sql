SELECT DISTINCT md.chembl_id, cs.canonical_smiles,
  act.standard_type, act.standard_value, act.standard_units
FROM activities act
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE td.chembl_id = 'CHEMBL221'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '='
  AND cs.canonical_smiles IS NOT NULL
ORDER BY act.standard_value
LIMIT 500
