SELECT DISTINCT
  m.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles,
  r.compound_key,
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
FROM molecule_dictionary m
JOIN compound_records r ON m.molregno = r.molregno
JOIN docs d ON r.doc_id = d.doc_id
JOIN activities act ON r.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND td.pref_name = 'Cytochrome P450 3A4'
  AND td.tax_id = 9606
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
