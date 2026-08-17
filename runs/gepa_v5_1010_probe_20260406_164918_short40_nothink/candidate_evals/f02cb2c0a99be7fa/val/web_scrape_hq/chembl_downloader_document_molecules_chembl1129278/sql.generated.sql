SELECT m.chembl_id AS molecule_chembl_id,
       m.pref_name AS molecule_name,
       m.max_phase AS max_phase,
       m.molecule_type AS molecule_type,
       cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
LEFT JOIN compound_records cr ON m.molregno = cr.molregno
LEFT JOIN compound_structures cs ON cr.molregno = cs.molregno
WHERE cr.doc_id = (SELECT doc_id FROM docs WHERE chembl_id = 'CHEMBL1129278')
ORDER BY molecule_chembl_id;
