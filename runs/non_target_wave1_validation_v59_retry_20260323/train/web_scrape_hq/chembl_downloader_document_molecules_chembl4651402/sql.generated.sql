SELECT DISTINCT
  md.chembl_id,
  cr.compound_name,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_records cr ON md.molregno = cr.molregno
JOIN docs d ON cr.doc_id = d.doc_id
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE d.chembl_id = 'CHEMBL4651402'
ORDER BY md.chembl_id, cr.compound_name, cs.canonical_smiles
