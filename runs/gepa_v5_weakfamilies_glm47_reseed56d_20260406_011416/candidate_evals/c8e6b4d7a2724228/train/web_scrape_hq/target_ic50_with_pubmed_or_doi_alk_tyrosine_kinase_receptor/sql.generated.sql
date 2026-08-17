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
  NULLIF(act.activity_comment, 'Not Active') AS activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN activities act ON md.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN docs d ON act.doc_id = d.doc_id
JOIN compound_records cr ON act.record_id = cr.record_id
WHERE td.chembl_id = 'CHEMBL4247'
  AND act.standard_type = 'IC50'
ORDER BY
  md.chembl_id ASC,
  cs.canonical_smiles ASC,
  cr.compound_key ASC,
  COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) ASC,
  a.description ASC,
  act.standard_type ASC,
  act.standard_relation ASC,
  act.standard_value ASC,
  act.standard_units ASC,
  NULLIF(act.activity_comment, 'Not Active') ASC,
  td.chembl_id ASC,
  td.pref_name ASC,
  td.organism ASC
