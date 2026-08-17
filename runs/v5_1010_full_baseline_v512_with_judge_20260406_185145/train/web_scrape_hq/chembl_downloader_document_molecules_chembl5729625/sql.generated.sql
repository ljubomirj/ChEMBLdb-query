SELECT m.chembl_id AS molecule_chembl_id,
       m.pref_name AS molecule_name,
       cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN compound_records cr ON m.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
JOIN activities act ON cr.record_id = act.record_id
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE d.chembl_id = 'CHEMBL5729625'
  AND cs.canonical_smiles IS NOT NULL
GROUP BY m.chembl_id, m.pref_name, cs.canonical_smiles
ORDER BY m.chembl_id, m.pref_name, cs.canonical_smiles;
