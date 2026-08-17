SELECT DISTINCT m.chembl_id AS molecule_chembl_id, m.pref_name AS compound_name, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN compound_records cr ON m.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE d.chembl_id = 'CHEMBL5729657';
