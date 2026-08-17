SELECT DISTINCT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  d.pubmed_id AS pubmed_id_or_doi,
  a.description AS assay_description,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units,
  a.activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
JOIN molecule_dictionary child ON child.molregno = mh.molregno
LEFT JOIN compound_records cr ON cr.molregno = child.molregno
JOIN docs d ON d.doc_id = cr.doc_id
JOIN activities a ON a.record_id = cr.record_id
JOIN assays ass ON ass.assay_id = a.assay_id
JOIN target_dictionary t ON t.tid = ass.tid
LEFT JOIN compound_structures cs ON cs.molregno = child.molregno
WHERE parent.chembl_id = 'CHEMBL3182437'
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND t.chembl_id = 'CHEMBL3430885'
ORDER BY compound_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism;
