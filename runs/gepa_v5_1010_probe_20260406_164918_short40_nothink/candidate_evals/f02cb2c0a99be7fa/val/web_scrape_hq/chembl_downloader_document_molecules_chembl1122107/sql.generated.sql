SELECT m.chembl_id AS molecule_chembl_id,
       m.pref_name AS molecule_name,
       m.max_phase,
       m.molecule_type,
       cs.canonical_smiles
FROM molecule_dictionary m
JOIN compound_records r ON m.molregno = r.molregno
JOIN docs d ON r.doc_id = d.doc_id
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE d.chembl_id = 'CHEMBL1122107'
ORDER BY molecule_chembl_id;
