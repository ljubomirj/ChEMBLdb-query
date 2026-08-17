SELECT DISTINCT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type AS standard_type,
  act.standard_relation AS standard_relation,
  act.standard_value AS standard_value,
  act.standard_units AS standard_units,
  act.activity_comment AS activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM activities act INDEXED BY fk_act_assay_id
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN docs d ON act.doc_id = d.doc_id
LEFT JOIN compound_records cr ON act.record_id = cr.record_id
WHERE act.assay_id IN (
    SELECT a2.assay_id
    FROM assays a2
    JOIN target_dictionary td2 ON a2.tid = td2.tid
    WHERE td2.chembl_id = 'CHEMBL1741186'
      AND td2.target_type = 'SINGLE PROTEIN'
      AND td2.organism = 'Homo sapiens'
)
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND td.chembl_id = 'CHEMBL1741186'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.organism = 'Homo sapiens'
  AND cs.canonical_smiles IS NOT NULL
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)