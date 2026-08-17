SELECT
  m.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(act.pubmed_id, act.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM molecule_dictionary m
JOIN activities act ON m.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON m.molregno = cs.molregno
JOIN compound_records cr ON m.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
WHERE a.assay_organism = 'Homo sapiens'
  AND a.chembl_id = 'CHEMBL333'
  AND act.bao_endpoint = 'IC50'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units IS NOT NULL
  AND (act.pubmed_id IS NOT NULL OR act.doi IS NOT NULL)
  AND act.standard_value IS NOT NULL
ORDER BY
  molecule_chembl_id,
  canonical_smiles,
  compound_key,
  pubmed_id_or_doi,
  assay_description,
  standard_type,
  standard_relation,
  standard_value,
  standard_units,
  activity_comment,
  target_chembl_id,
  target_name,
  target_organism
