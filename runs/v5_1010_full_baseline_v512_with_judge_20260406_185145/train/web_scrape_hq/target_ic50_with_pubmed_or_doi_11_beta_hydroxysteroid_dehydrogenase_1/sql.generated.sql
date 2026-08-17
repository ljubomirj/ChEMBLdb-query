SELECT DISTINCT
  m.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  a.standard_type AS standard_type,
  a.standard_relation AS standard_relation,
  a.standard_value AS standard_value,
  a.standard_units AS standard_units,
  a.activity_comment AS activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary t ON ass.tid = t.tid
JOIN molecule_dictionary m ON m.molregno = a.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN compound_records cr ON cr.molregno = m.molregno
JOIN docs d ON d.doc_id = a.doc_id
WHERE m.chembl_id = 'CHEMBL4235'
  AND t.target_type = 'SINGLE PROTEIN'
  AND t.pref_name = '11-beta-hydroxysteroid dehydrogenase 1'
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_units = 'nM'
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
