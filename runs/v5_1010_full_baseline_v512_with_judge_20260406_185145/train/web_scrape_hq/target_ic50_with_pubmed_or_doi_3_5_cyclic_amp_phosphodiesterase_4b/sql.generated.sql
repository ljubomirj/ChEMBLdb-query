SELECT DISTINCT
  m.chembl_id AS molecule_chembl_id,
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
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_records cr ON cr.record_id = act.record_id
JOIN molecule_dictionary m ON m.molregno = cr.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN docs d ON d.doc_id = cr.doc_id
WHERE act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND a.assay_type = 'F'
  AND a.assay_organism = 'Homo sapiens'
  AND td.chembl_id = 'CHEMBL275'
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
LIMIT 2000
