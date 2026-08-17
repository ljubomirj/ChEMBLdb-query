SELECT DISTINCT
  md.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units,
  a.activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM molecule_dictionary md
JOIN activities a ON md.molregno = a.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN compound_records cr ON md.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
WHERE ass.assay_organism = 'Homo sapiens'
  AND td.pref_name = 'Beta-secretase 1'
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
  AND a.standard_units = 'nM'
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
  AND cs.canonical_smiles IS NOT NULL
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
