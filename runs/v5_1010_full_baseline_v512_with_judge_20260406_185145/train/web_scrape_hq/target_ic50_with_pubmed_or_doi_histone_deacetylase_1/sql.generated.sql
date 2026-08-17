SELECT DISTINCT
  m.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  d.pubmed_id AS pubmed_id_or_doi,
  a.description AS assay_description,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units,
  a.activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM activities a
JOIN assays a2 ON a.assay_id = a2.assay_id
JOIN target_dictionary td ON a2.tid = td.tid
JOIN molecule_dictionary m ON a.molregno = m.molregno
JOIN compound_records cr ON m.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_units = 'nM'
  AND a.standard_value IS NOT NULL
  AND a.standard_value <> 0
  AND a.activity_comment IS NOT NULL
  AND a.potential_duplicate = 0
  AND a.type = 'IC50'
  AND a.relation = '>'
  AND a.value IS NULL
  AND a.units IS NULL
  AND a.text_value IS NULL
  AND a.standard_text_value IS NULL
  AND a.standard_flag = 1
  AND a.potential_duplicate = 0
  AND td.chembl_id = 'CHEMBL325'
  AND td.tax_id = 9606
  AND a.assay_organism = 'Homo sapiens';
