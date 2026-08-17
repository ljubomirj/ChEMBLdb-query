SELECT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) AS pubmed_id_or_doi,
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
JOIN compound_structures cs ON cs.molregno = child.molregno
JOIN compound_records cr ON cr.molregno = child.molregno
JOIN activities act ON act.record_id = cr.record_id
JOIN docs d ON d.doc_id = act.doc_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
WHERE parent.chembl_id = 'CHEMBL1336'
  AND td.chembl_id = 'CHEMBL279'
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
ORDER BY
  child.chembl_id,
  cr.compound_key,
  COALESCE(CAST(d.pubmed_id AS TEXT), d.doi),
  a.description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  td.chembl_id,
  td.pref_name,
  td.organism
