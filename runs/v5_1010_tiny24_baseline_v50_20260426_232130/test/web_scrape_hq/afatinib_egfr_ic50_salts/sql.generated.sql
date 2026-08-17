SELECT DISTINCT
  m.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  r.compound_key,
  COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
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
JOIN molecule_dictionary m ON m.molregno = mh.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN compound_records r ON r.molregno = m.molregno
JOIN docs d ON d.doc_id = r.doc_id
JOIN activities act ON act.record_id = r.record_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary t ON t.tid = act.tid
WHERE parent.chembl_id = 'CHEMBL1173655'
  AND t.chembl_id = 'CHEMBL203'
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
