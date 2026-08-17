SELECT DISTINCT
  child_mol.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  d.pubmed_id AS pubmed_id_or_doi,
  ass.description AS assay_description,
  a.standard_type AS standard_type,
  a.standard_relation AS standard_relation,
  a.standard_value AS standard_value,
  a.standard_units AS standard_units,
  a.activity_comment AS activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary AS parent_mol
JOIN molecule_hierarchy AS mh ON mh.parent_molregno = parent_mol.molregno
JOIN molecule_dictionary AS child_mol ON child_mol.molregno = mh.molregno
LEFT JOIN compound_records AS cr ON cr.molregno = child_mol.molregno
LEFT JOIN docs AS d ON d.doc_id = cr.doc_id
LEFT JOIN activities AS a ON a.record_id = cr.record_id
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_units = 'nM'
  AND a.standard_value IS NOT NULL
LEFT JOIN assays AS ass ON ass.assay_id = a.assay_id
LEFT JOIN target_dictionary AS t ON t.tid = a.tid
LEFT JOIN compound_structures AS cs ON cs.molregno = child_mol.molregno
WHERE parent_mol.chembl_id = 'CHEMBL1173655'
  AND t.chembl_id = 'CHEMBL203';
