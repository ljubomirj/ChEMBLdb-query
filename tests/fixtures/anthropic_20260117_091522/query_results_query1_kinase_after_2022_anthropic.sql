WITH kinase_target_ids AS (
  SELECT DISTINCT td.tid
  FROM target_dictionary td
  INNER JOIN target_components tc ON td.tid = tc.tid
  INNER JOIN component_class cc ON tc.component_id = cc.component_id
  INNER JOIN protein_classification pc ON cc.protein_class_id = pc.protein_class_id
  WHERE pc.pref_name LIKE '%kinase%'
)
SELECT 
  cs.canonical_smiles,
  cil.chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi,
  a.standard_value AS ic50_value
FROM activities a
INNER JOIN assays ass ON a.assay_id = ass.assay_id
INNER JOIN docs d ON ass.doc_id = d.doc_id
INNER JOIN target_dictionary td ON ass.tid = td.tid
INNER JOIN molecule_dictionary md ON a.molregno = md.molregno
INNER JOIN compound_structures cs ON md.molregno = cs.molregno
INNER JOIN chembl_id_lookup cil ON md.molregno = cil.entity_id AND cil.entity_type = 'COMPOUND'
WHERE a.standard_type = 'IC50'
  AND a.standard_value IS NOT NULL
  AND d.year > 2022
  AND ass.tid IN (SELECT tid FROM kinase_target_ids)
ORDER BY d.year DESC, a.standard_value ASC
