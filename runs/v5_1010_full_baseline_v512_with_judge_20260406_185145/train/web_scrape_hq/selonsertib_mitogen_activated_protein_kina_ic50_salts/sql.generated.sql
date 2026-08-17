SELECT DISTINCT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  r.compound_key,
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
LEFT JOIN compound_structures cs ON cs.molregno = child.molregno
JOIN compound_records r ON r.molregno = child.molregno
JOIN docs d ON d.doc_id = r.doc_id
JOIN activities a ON a.record_id = r.record_id
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
  AND a.standard_units = 'nM'
JOIN assays ON a.assay_id = assays.assay_id
JOIN target_dictionary t ON t.tid = assays.tid
  AND t.chembl_id = 'CHEMBL5285'
WHERE parent.chembl_id = 'CHEMBL3916717'
ORDER BY compound_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism;
