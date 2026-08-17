SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON m.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.chembl_id = 'CHEMBL224'
  AND a.assay_organism = 'Homo sapiens'
  AND act.type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND act.standard_type = 'IC50'
  AND act.standard_flag = 1
  AND act.potential_duplicate = 0
  AND a.assay_type = 'B'
  AND a.assay_category = 'Binding'
  AND a.assay_test_type IS NULL
  AND a.assay_organism = 'Homo sapiens'
  AND act.activity_comment IS NOT NULL
  AND act.data_validity_comment IS NOT NULL;
