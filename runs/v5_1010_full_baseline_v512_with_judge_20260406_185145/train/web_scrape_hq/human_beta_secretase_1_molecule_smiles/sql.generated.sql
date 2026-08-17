SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.tid = 4822
  AND a.assay_organism = 'Homo sapiens'
  AND act.type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
ORDER BY m.chembl_id;
