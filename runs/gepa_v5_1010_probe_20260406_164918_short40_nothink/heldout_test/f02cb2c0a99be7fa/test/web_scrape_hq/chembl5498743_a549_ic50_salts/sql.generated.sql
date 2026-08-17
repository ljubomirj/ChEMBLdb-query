SELECT DISTINCT
  m_child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units,
  a.activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary m_parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = m_parent.molregno
JOIN molecule_dictionary m_child ON m_child.molregno = mh.molregno
LEFT JOIN compound_records cr ON cr.molregno = m_child.molregno
LEFT JOIN docs d ON d.doc_id = cr.doc_id
LEFT JOIN activities a ON a.record_id = cr.record_id
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
LEFT JOIN assays ass ON ass.assay_id = a.assay_id
LEFT JOIN target_dictionary t ON t.tid = ass.tid
LEFT JOIN compound_structures cs ON cs.molregno = m_child.molregno
WHERE m_parent.chembl_id = 'CHEMBL5498743'
  AND ass.assay_organism = 'A549'
  AND t.chembl_id = 'CHEMBL392'
ORDER BY compound_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism;
