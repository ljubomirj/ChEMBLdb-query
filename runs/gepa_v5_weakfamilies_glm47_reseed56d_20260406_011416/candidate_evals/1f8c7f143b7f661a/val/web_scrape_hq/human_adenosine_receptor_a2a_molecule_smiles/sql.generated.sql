SELECT DISTINCT md.chembl_id AS molecule_chembl_id, cs.canonical_smiles
FROM molecule_dictionary md
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE td.pref_name = 'Adenosine A2a receptor'
ORDER BY md.chembl_id
