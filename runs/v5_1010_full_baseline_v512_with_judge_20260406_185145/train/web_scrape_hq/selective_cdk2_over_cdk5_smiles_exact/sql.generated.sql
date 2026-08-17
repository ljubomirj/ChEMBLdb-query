SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td1 ON td1.tid = a.tid
JOIN target_dictionary td2 ON td2.tid = 4036
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE a.assay_organism = 'Caenorhabditis elegans'
  AND act.standard_relation = '='
  AND act.standard_value < 50
  AND act.standard_units = 'nM'
  AND act.activity_type = 'IC50'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value > 200
  AND act.standard_units = 'nM'
  AND act.activity_type = 'IC50'
  AND act.standard_type = 'IC50'
