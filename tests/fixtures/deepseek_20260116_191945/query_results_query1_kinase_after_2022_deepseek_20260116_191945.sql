WITH kinase_targets AS (
    SELECT DISTINCT tc.tid
    FROM target_components tc
    JOIN component_class cc ON tc.component_id = cc.component_id
    JOIN protein_classification pc ON cc.protein_class_id = pc.protein_class_id
    WHERE (pc.pref_name LIKE '%kinase%' OR pc.protein_class_desc LIKE '%kinase%')
)
SELECT 
    cs.canonical_smiles,
    md.chembl_id AS compound_chembl_id,
    td.pref_name AS target_name,
    d.year AS publication_year,
    d.doi AS article_doi,
    a.standard_value AS IC50
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN kinase_targets kt ON td.tid = kt.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN docs d ON a.doc_id = d.doc_id
WHERE a.standard_type = 'IC50'
    AND d.year > 2022
    AND ass.confidence_score >= 8;
