SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles, act.standard_type, act.standard_value, act.standard_units
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary m ON m.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.target_type = 'SINGLE PROTEIN'
  AND a.assay_organism = 'Homo sapiens'
  AND act.bao_endpoint = 'EC50'
  AND act.standard_type = 'EC50'
  AND act.standard_value < 100
  AND act.standard_units = 'nM'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units IS NOT NULL
ORDER BY m.chembl_id, cs.canonical_smiles, act.standard_type, act.standard_value, act.standard_units
LIMIT 500
