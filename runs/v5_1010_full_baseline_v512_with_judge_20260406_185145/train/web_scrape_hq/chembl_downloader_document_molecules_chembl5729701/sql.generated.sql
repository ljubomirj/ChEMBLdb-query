SELECT DISTINCT m.chembl_id AS molecule_chembl_id, m.pref_name AS compound_name, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN compound_records cr ON m.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
JOIN activities act ON cr.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE d.chembl_id = 'CHEMBL5729701';
