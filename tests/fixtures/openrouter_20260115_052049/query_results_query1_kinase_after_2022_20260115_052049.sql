SELECT
  cs.canonical_smiles AS compound_smiles,
  md.chembl_id AS compound_chembl_id,
  td.pref_name AS target_name,
  d.year AS publication_year,
  d.doi AS article_doi,
  a.standard_value AS ic50_value,
  a.standard_units AS ic50_units
FROM activities a
JOIN assays s ON a.assay_id = s.assay_id
JOIN docs d ON s.doc_id = d.doc_id
JOIN target_dictionary td ON s.tid = td.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON a.molregno = cs.molregno
WHERE d.year > 2022
  AND a.standard_type = 'IC50'
  AND s.confidence_score >= 8
  AND EXISTS (
    SELECT 1
    FROM target_components tc
    JOIN component_class cc ON tc.component_id = cc.component_id
    JOIN protein_classification pc ON cc.protein_class_id = pc.protein_class_id
    WHERE tc.tid = td.tid
      AND LOWER(pc.pref_name) LIKE '%kinase%'
  );
