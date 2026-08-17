SELECT
  m.chembl_id AS molecule_chembl_id,
  cs.canonical_smiles,
  cr.compound_key,
  d.pubmed_id,
  d.doi AS pubmed_id_or_doi,
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
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN molecule_dictionary m ON cr.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
JOIN docs d ON cr.doc_id = d.doc_id
WHERE act.bao_endpoint = 'BAO_0000190'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_units = 'nM'
  AND act.standard_value IS NOT NULL
  AND act.standard_value > 0
  AND td.pref_name = 'Phosphatidylinositol 4,5-bisphosphate 3‑kinase catalytic subunit alpha'
  AND td.tax_id = 9606
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
  AND cs.canonical_smiles IS NOT NULL
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
