SELECT DISTINCT
  m.chembl_id AS compound_chembl_id,
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
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN compound_records cr ON cr.molregno = m.molregno
WHERE act.activity_type = 'IC50'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND a.assay_organism = 'Homo sapiens'
  AND td.pref_name = 'Mitogen‑activated protein kinase 14'
ORDER BY compound_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
LIMIT 1000
