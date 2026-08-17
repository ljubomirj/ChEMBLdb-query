SELECT DISTINCT cs.canonical_smiles, md.chembl_id AS molecule_chembl_id, td.pref_name AS target_pref_name, d.year AS publication_year, d.doi, a.standard_value AS ic50_nM 
FROM activities a 
JOIN assays ass ON a.assay_id = ass.assay_id 
JOIN target_dictionary td ON ass.tid = td.tid 
JOIN molecule_dictionary md ON a.molregno = md.molregno 
JOIN compound_structures cs ON a.molregno = cs.molregno 
JOIN docs d ON a.doc_id = d.doc_id 
WHERE a.standard_type = 'IC50' AND a.standard_units = 'nM' AND a.standard_value IS NOT NULL AND td.pref_name LIKE '%kinase%' AND d.year > 2022 
ORDER BY d.year DESC;
