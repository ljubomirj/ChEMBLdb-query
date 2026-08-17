SELECT
  m.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  r.compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
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
JOIN compound_records r ON r.molregno = m.molregno
JOIN activities act ON act.record_id = r.record_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary t ON t.tid = a.tid
JOIN docs d ON d.doc_id = r.doc_id
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE parent.chembl_id = 'CHEMBL3182437'
  AND t.chembl_id = 'CHEMBL3430885'
  AND act.standard_type = 'IC50'
ORDER BY
  compound_chembl_id ASC,
  canonical_smiles ASC,
  compound_key ASC,
  pubmed_id_or_doi ASC,
  assay_description ASC,
  standard_type ASC,
  standard_relation ASC,
  standard_value ASC,
  standard_units ASC,
  activity_comment ASC,
  target_chembl_id ASC,
  target_name ASC,
  target_organism ASC
