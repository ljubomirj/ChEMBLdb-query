SELECT
  md.chembl_id AS compound_chembl_id,
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
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_records cr ON cr.record_id = act.record_id
JOIN docs d ON d.doc_id = cr.doc_id
WHERE td.chembl_id = 'CHEMBL3717'
  AND act.standard_type = 'IC50'
  AND cs.canonical_smiles IS NOT NULL
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
ORDER BY
  md.chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(CAST(d.pubmed_id AS TEXT), d.doi),
  a.description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  td.chembl_id,
  td.pref_name,
  td.organism
