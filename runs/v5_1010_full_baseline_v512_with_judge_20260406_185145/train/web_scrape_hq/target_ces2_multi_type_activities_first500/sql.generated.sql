SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles, act.standard_type, act.standard_value, act.standard_units
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary m ON act.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.chembl_id = 'CHEMBL206'
  AND act.standard_type = 'IC50'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '='
ORDER BY act.standard_value
LIMIT 500;
