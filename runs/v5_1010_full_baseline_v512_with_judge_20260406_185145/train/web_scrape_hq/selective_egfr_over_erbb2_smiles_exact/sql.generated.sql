SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE act.standard_relation = '='
  AND act.standard_units = 'nM'
  AND act.standard_value < 50
  AND act.standard_value > 200
  AND act.activity_type = 'IC50'
  AND td.chembl_id = 'CHEMBL203'
  AND td.chembl_id = 'CHEMBL1824'
ORDER BY compound_chembl_id, canonical_smiles;
