SELECT DISTINCT
  m.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  p.pubmed_id AS pubmed_id_or_doi,
  a.description AS assay_description,
  a.standard_type AS standard_type,
  a.standard_relation AS standard_relation,
  a.standard_value AS standard_value,
  a.standard_units AS standard_units,
  a.activity_comment AS activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary m
JOIN activities a ON a.molregno = m.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary t ON ass.tid = t.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN compound_records cr ON m.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
JOIN (
  SELECT d.pubmed_id, d.doi
  FROM docs d
  WHERE d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL
) p ON (d.pubmed_id = p.pubmed_id OR d.doi = p.doi)
WHERE a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.bao_endpoint = 'BAO_0000190'
  AND ass.assay_organism = 'Homo sapiens'
  AND t.target_type = 'SINGLE PROTEIN'
  AND t.pref_name = 'Lysine-specific histone demethylase 1A'
  AND t.chembl_id = 'CHEMBL6136'
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
LIMIT 2000
