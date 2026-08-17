SELECT
  MD.chembl_id AS molecule_chembl_id,
  CS.canonical_smiles,
  CR.compound_key,
  COALESCE(PD.pubmed_id, PD.doi) AS pubmed_id_or_doi,
  AS.description AS assay_description,
  ACT.standard_type,
  ACT.standard_relation,
  ACT.standard_value,
  ACT.standard_units,
  ACT.activity_comment,
  TD.chembl_id AS target_chembl_id,
  TD.pref_name AS target_name,
  TD.organism AS target_organism
FROM molecule_dictionary MD
JOIN activities ACT ON MD.molregno = ACT.molregno
JOIN assays AS ON ACT.assay_id = AS.assay_id
JOIN target_dictionary TD ON AS.tid = TD.tid
JOIN compound_structures CS ON MD.molregno = CS.molregno
JOIN compound_records CR ON ACT.record_id = CR.record_id
JOIN docs D ON CR.doc_id = D.doc_id
JOIN (
  SELECT DISTINCT D.doc_id, D.pubmed_id, D.doi
  FROM docs D
  WHERE D.pubmed_id IS NOT NULL OR D.doi IS NOT NULL
) PD ON D.doc_id = PD.doc_id
WHERE MD.pref_name = 'C‑C chemokine receptor type 2'
  AND AS.assay_organism = 'Homo sapiens'
  AND ACT.standard_type = 'IC50'
  AND ACT.standard_relation = '='
  AND ACT.standard_value IS NOT NULL
  AND ACT.standard_units = 'nM'
  AND (PD.pubmed_id IS NOT NULL OR PD.doi IS NOT NULL)
ORDER BY molecule_chembl_id, canonical_smiles, compound_key, pubmed_id_or_doi, assay_description, standard_type, standard_relation, standard_value, standard_units, activity_comment, target_chembl_id, target_name, target_organism
