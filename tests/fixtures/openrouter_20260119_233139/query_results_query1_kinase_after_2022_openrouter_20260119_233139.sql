WITH kinase_tids AS (
  SELECT DISTINCT tc.tid
  FROM target_components tc
  JOIN component_class cc ON tc.component_id = cc.component_id
  JOIN protein_classification pc ON cc.protein_class_id = pc.protein_class_id
  WHERE lower(pc.pref_name) LIKE '%kinase%'
     OR lower(pc.protein_class_desc) LIKE '%kinase%'
)
SELECT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi AS article_doi,
  a.standard_relation AS ic50_standard_relation,
  a.standard_value AS ic50_standard_value,
  a.standard_units AS ic50_standard_units
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN docs d ON ass.doc_id = d.doc_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN kinase_tids kt ON td.tid = kt.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
LEFT JOIN compound_structures cs ON a.molregno = cs.molregno
WHERE a.standard_type = 'IC50'
  AND d.year > 2022;
