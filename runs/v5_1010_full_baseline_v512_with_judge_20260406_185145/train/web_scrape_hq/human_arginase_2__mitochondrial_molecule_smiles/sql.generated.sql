SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON m.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.pref_name = 'human arginase 2 (mitochondrial)'
  AND td.tax_id = 9606
  AND a.assay_organism = 'Homo sapiens'
  AND a.assay_type = 'B'
  AND a.assay_test_type = 'Binding'
  AND a.assay_category = 'In vitro inhibition'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND act.pchembl_value IS NOT NULL
  AND act.pchembl_value > 0
  AND act.pchembl_value <= 6.0
  AND act.potential_duplicate = 0
  AND act.standard_flag = 1
  AND act.type = 'IC50'
  AND act.relation = '>'
  AND act.value IS NULL
  AND act.units IS NULL
  AND act.text_value IS NULL
  AND act.standard_text_value IS NULL
  AND act.activity_comment IS NOT NULL
  AND act.data_validity_comment IS NOT NULL
  AND act.src_id IS NOT NULL
  AND act.doc_id IS NOT NULL
  AND act.record_id IS NOT NULL
  AND act.molregno IS NOT NULL
  AND a.assay_id IS NOT NULL
  AND a.tid IS NOT NULL
  AND td.tid IS NOT NULL
  AND a.assay_id = act.assay_id
  AND a.tid = td.tid
  AND a.assay_organism IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND td.pref_name IS NOT NULL
  AND td.pref_name = 'human arginase 2 (mitochondrial)'
  AND td.tax_id IS NOT NULL
  AND td.tax_id = 9606;
