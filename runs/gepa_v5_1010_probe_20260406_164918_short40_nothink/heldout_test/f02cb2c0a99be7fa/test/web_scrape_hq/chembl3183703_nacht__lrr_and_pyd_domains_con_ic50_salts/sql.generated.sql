SELECT DISTINCT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  r.compound_key AS compound_key,
  d.pubmed_id AS pubmed_id,
  d.doi AS doi,
  d.doi AS pubmed_id_or_doi,
  ass.description AS assay_description,
  a.standard_type AS standard_type,
  a.standard_relation AS standard_relation,
  a.standard_value AS standard_value,
  a.standard_units AS standard_units,
  a.activity_comment AS activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
JOIN molecule_dictionary child ON child.molregno = mh.molregno
LEFT JOIN compound_records r ON child.molregno = r.molregno
LEFT JOIN docs d ON r.doc_id = d.doc_id
LEFT JOIN activities a ON r.record_id = a.record_id
LEFT JOIN assays ass ON a.assay_id = ass.assay_id
LEFT JOIN target_dictionary t ON ass.tid = t.tid
LEFT JOIN compound_structures cs ON child.molregno = cs.molregno
WHERE parent.chembl_id = 'CHEMBL3183703'
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND ass.assay_organism = 'Homo sapiens'
ORDER BY compound_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism;
