SELECT DISTINCT
  md.chembl_id,
  cr.compound_name,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_records cr ON cr.molregno = md.molregno
JOIN docs d ON d.doc_id = cr.doc_id
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE d.chembl_id = 'CHEMBL1123858'
  AND cs.canonical_smiles IS NOT NULL
ORDER BY md.chembl_id ASC, cr.compound_name ASC, cs.canonical_smiles ASC
