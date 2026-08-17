SELECT DISTINCT
  m.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units,
  a.activity_comment,
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
WHERE m.chembl_id = 'CHEMBL1936'
  AND t.target_type = 'SINGLE PROTEIN'
  AND t.organism = 'Homo sapiens'
  AND cs.canonical_smiles IS NOT NULL
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
  AND a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.standard_units = 'nM'
  AND a.standard_value IS NOT NULL
ORDER BY
  m.chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  COALESCE(d.pubmed_id, d.doi),
  a.description,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units,
  a.activity_comment,
  t.chembl_id,
  t.pref_name,
  t.organism;
