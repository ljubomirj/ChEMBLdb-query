SELECT DISTINCT m.chembl_id AS molecule_chembl_id, m.pref_name AS molecule_name, m.max_phase, m.molecule_type, cs.canonical_smiles
FROM molecule_dictionary m
LEFT JOIN compound_records cr ON m.molregno = cr.molregno
LEFT JOIN compound_structures cs ON cr.molregno = cs.molregno
LEFT JOIN docs d ON cr.doc_id = d.doc_id
WHERE d.chembl_id = 'CHEMBL1135903'
ORDER BY molecule_chembl_id;
