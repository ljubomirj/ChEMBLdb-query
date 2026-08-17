WITH kinase_tids AS (
  SELECT DISTINCT tc.tid
  FROM target_components tc
  JOIN component_class cc ON cc.component_id = tc.component_id
  JOIN protein_classification pc ON pc.protein_class_id = cc.protein_class_id
  WHERE LOWER(pc.pref_name) LIKE '%kinase%'
)
SELECT
  cs.canonical_smiles AS smiles,
  md.chembl_id AS compound_chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi AS doi,
  act.standard_value AS ic50_value,
  act.standard_units AS ic50_units
FROM activities act
JOIN assays ass ON ass.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = ass.tid
JOIN kinase_tids kt ON kt.tid = td.tid
JOIN molecule_dictionary md ON md.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN docs d ON d.doc_id = COALESCE(ass.doc_id, act.doc_id)
WHERE act.standard_type = 'IC50'
  AND d.year > 2022
ORDER BY
  publication_year DESC,
  (ic50_value IS NULL) ASC,
  ic50_value ASC;
