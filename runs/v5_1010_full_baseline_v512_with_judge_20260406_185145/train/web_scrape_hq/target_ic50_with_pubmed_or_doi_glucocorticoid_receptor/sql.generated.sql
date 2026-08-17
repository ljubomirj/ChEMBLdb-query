SELECT DISTINCT
  m.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  d.pubmed_id AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN compound_records cr ON cr.molregno = m.molregno
JOIN docs d ON cr.doc_id = d.doc_id
WHERE act.activity_type = 'IC50'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_units = 'nM'
  AND td.pref_name = 'Glucocorticoid Receptor'
  AND td.tax_id = 9606
  AND act.pchembl_value IS NOT NULL
  AND act.standard_value IS NOT NULL
  AND act.standard_units IS NOT NULL
  AND act.standard_relation IS NOT NULL
  AND act.activity_comment IS NOT NULL
  AND d.pubmed_id IS NOT NULL;
