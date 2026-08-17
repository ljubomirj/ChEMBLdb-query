SELECT DISTINCT
  md.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  COALESCE(act.pubmed_id, act.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type AS standard_type,
  act.standard_relation AS standard_relation,
  act.standard_value AS standard_value,
  act.standard_units AS standard_units,
  act.activity_comment AS activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM activities act
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN molecule_dictionary md ON cr.molregno = md.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE td.tid = 274
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_units = 'nM'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.pref_name = 'C-C chemokine receptor type 5'
  AND td.tax_id = 9606
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
LIMIT 2000
