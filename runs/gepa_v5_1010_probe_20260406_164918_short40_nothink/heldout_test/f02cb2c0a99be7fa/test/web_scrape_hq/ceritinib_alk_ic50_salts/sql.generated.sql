SELECT DISTINCT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
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
FROM molecule_dictionary parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
JOIN molecule_dictionary child ON child.molregno = mh.molregno
LEFT JOIN compound_structures cs ON cs.molregno = child.molregno
LEFT JOIN compound_records cr ON cr.molregno = child.molregno
LEFT JOIN docs d ON cr.doc_id = d.doc_id
JOIN activities act ON cr.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON act.tid = td.tid
WHERE parent.chembl_id = 'CHEMBL2403108'
  AND act.bao_endpoint = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND a.assay_organism = 'Homo sapiens'
  AND td.chembl_id = 'CHEMBL4247'
ORDER BY compound_chembl_id, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, target_chembl_id, target_name, target_organism;
