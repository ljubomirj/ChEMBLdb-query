SELECT DISTINCT
  m.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM activities act
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN molecule_dictionary m ON cr.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN docs d ON cr.doc_id = d.doc_id
WHERE act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND a.assay_organism = 'Homo sapiens'
  AND td.pref_name = 'ALK tyrosine kinase receptor'
  AND td.chembl_id = 'CHEMBL4247'
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
