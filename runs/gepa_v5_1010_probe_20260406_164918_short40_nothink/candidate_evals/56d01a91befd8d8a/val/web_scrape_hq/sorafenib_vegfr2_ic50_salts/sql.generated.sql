SELECT DISTINCT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  d.pubmed_id AS pubmed_id_or_doi,
  ass.description AS assay_description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
JOIN molecule_dictionary child ON child.molregno = mh.molregno
LEFT JOIN compound_structures cs ON cs.molregno = child.molregno
LEFT JOIN compound_records cr ON cr.molregno = child.molregno
LEFT JOIN docs d ON cr.doc_id = d.doc_id
LEFT JOIN activities act ON cr.record_id = act.record_id
LEFT JOIN assays ass ON act.assay_id = ass.assay_id
LEFT JOIN target_dictionary t ON ass.tid = t.tid
WHERE parent.chembl_id = 'CHEMBL1336'
  AND t.pref_name = 'Vascular endothelial growth factor receptor 2'
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
ORDER BY compound_chembl_id, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, target_chembl_id, target_name, target_organism;
