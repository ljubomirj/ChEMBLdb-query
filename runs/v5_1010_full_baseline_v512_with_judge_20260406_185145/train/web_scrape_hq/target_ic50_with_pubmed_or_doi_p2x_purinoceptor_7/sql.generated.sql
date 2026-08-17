SELECT
  act.molregno AS molecule_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
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
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
JOIN docs d ON cr.doc_id = d.doc_id
WHERE act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.bao_endpoint = 'BAO_0000006'
  AND act.standard_units = 'nM'
  AND act.activity_comment IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND a.tid = 4805
  AND td.chembl_id = 'CHEMBL4805'
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
LIMIT 2000
