SELECT DISTINCT
  m.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
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
JOIN compound_records cr ON a.record_id = cr.record_id
JOIN molecule_dictionary m ON cr.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
JOIN docs d ON cr.doc_id = d.doc_id
WHERE a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_units = 'nM'
  AND a.standard_value IS NOT NULL
  AND a.activity_comment IS NOT NULL
  AND a.pchembl_value IS NOT NULL
  AND a2.assay_organism = 'Homo sapiens'
  AND td.pref_name = 'Prostaglandin G/H synthase 1'
ORDER BY compound_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
