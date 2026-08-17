SELECT DISTINCT
  m_child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  d.pubmed_id AS pubmed_id_or_doi,
  ass.description AS assay_description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM molecule_dictionary m_parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = m_parent.molregno
JOIN molecule_dictionary m_child ON m_child.molregno = mh.molregno
LEFT JOIN compound_structures cs ON cs.molregno = m_child.molregno
JOIN compound_records cr ON cr.molregno = m_child.molregno
JOIN docs d ON d.doc_id = cr.doc_id
JOIN activities act ON act.record_id = cr.record_id
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
JOIN assays ass ON ass.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = ass.tid
WHERE m_parent.chembl_id = 'CHEMBL3182437'
  AND ass.assay_organism = 'Homo sapiens'
  AND td.chembl_id = 'CHEMBL3430885'
ORDER BY
  m_child.chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  d.pubmed_id,
  ass.description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  td.chembl_id,
  td.pref_name,
  td.organism;
