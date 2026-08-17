SELECT DISTINCT
  m.chembl_id,
  r.compound_name,
  s.canonical_smiles
FROM molecule_dictionary m
JOIN compound_records r ON m.molregno = r.molregno
JOIN docs d ON r.doc_id = d.doc_id
JOIN compound_structures s ON m.molregno = s.molregno
WHERE d.chembl_id = 'CHEMBL1139796'
  AND s.canonical_smiles IS NOT NULL
ORDER BY m.chembl_id, r.compound_name, s.canonical_smiles
