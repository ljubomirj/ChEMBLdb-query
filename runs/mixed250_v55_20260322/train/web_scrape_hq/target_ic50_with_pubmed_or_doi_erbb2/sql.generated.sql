SELECT DISTINCT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN docs d ON act.doc_id = d.doc_id
WHERE td.chembl_id = 'CHEMBL1824'
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.organism = 'Homo sapiens'
  AND cs.canonical_smiles IS NOT NULL
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
