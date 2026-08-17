WITH
docs_2023 AS (
  SELECT doc_id, year, doi
  FROM docs
  WHERE year > 2022
),
assays_2023 AS (
  SELECT a.assay_id, a.tid, a.doc_id
  FROM assays a
  JOIN docs_2023 d
    ON d.doc_id = a.doc_id
  WHERE a.tid IS NOT NULL
),
tids_in_scope AS (
  SELECT DISTINCT tid
  FROM assays_2023
),
kinase_tids AS (
  SELECT DISTINCT tis.tid
  FROM tids_in_scope tis
  JOIN target_components tc
    ON tc.tid = tis.tid
  JOIN component_class cc
    ON cc.component_id = tc.component_id
  JOIN protein_classification pc
    ON pc.protein_class_id = cc.protein_class_id
  WHERE lower(pc.pref_name) LIKE '%kinase%'
     OR lower(pc.short_name) LIKE '%kinase%'
     OR lower(pc.protein_class_desc) LIKE '%kinase%'
),
activities_ic50 AS (
  SELECT a.activity_id, a.assay_id, a.molregno, a.standard_value
  FROM activities a
  JOIN assays_2023 s
    ON s.assay_id = a.assay_id
  WHERE a.standard_type = 'IC50'
    AND a.molregno IS NOT NULL
    AND a.standard_value IS NOT NULL
)
SELECT
  cs.canonical_smiles AS smiles,
  md.chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi,
  ai.standard_value AS ic50
FROM activities_ic50 ai
JOIN assays_2023 s
  ON s.assay_id = ai.assay_id
JOIN kinase_tids kt
  ON kt.tid = s.tid
JOIN target_dictionary td
  ON td.tid = s.tid
JOIN docs_2023 d
  ON d.doc_id = s.doc_id
JOIN molecule_dictionary md
  ON md.molregno = ai.molregno
JOIN compound_structures cs
  ON cs.molregno = md.molregno;
