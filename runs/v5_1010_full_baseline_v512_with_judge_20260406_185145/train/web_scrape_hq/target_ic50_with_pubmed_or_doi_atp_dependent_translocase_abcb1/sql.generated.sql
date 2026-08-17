SELECT
  MD.chembl_id AS compound_chembl_id,
  CS.canonical_smiles,
  CR.compound_key,
  COALESCE(ACT.pubmed_id, ACT.doi) AS pubmed_id_or_doi,
  ASY.description AS assay_description,
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
JOIN assays ASY ON ACT.assay_id = ASY.assay_id
JOIN target_dictionary TD ON ASY.tid = TD.tid
JOIN compound_structures CS ON MD.molregno = CS.molregno
JOIN compound_records CR ON MD.molregno = CR.molregno
JOIN docs DOC ON ACT.doc_id = DOC.doc_id
WHERE MD.molregno IN (
  SELECT MD2.molregno
  FROM molecule_dictionary MD2
  JOIN assays ASY2 ON MD2.molregno = ASY2.molregno
  JOIN activities ACT2 ON ASY2.assay_id = ACT2.assay_id
  JOIN target_dictionary TD2 ON ASY2.tid = TD2.tid
  WHERE TD2.pref_name = 'ATP‑dependent translocase ABCB1'
    AND TD2.target_type = 'PROTEIN'
    AND TD2.organism = 'Homo sapiens'
    AND ACT2.standard_type = 'IC50'
    AND ACT2.standard_units = 'nM'
    AND ACT2.standard_relation = '='
    AND ACT2.standard_value IS NOT NULL
    AND (ACT2.pubmed_id IS NOT NULL OR ACT2.doi IS NOT NULL)
)
  AND (ACT.pubmed_id IS NOT NULL OR ACT.doi IS NOT NULL)
  AND CS.canonical_smiles IS NOT NULL
ORDER BY
  compound_chembl_id,
  canonical_smiles,
  compound_key,
  pubmed_id_or_doi,
  assay_description,
  standard_type,
  standard_relation,
  standard_value,
  standard_units,
  activity_comment,
  target_chembl_id,
  target_name,
  target_organism;
