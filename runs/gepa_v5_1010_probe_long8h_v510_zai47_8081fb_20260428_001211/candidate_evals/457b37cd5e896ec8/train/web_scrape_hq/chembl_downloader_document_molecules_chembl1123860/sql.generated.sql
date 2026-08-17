SELECT DISTINCT
    md.chembl_id,
    cr.compound_name,
    cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_records cr ON md.molregno = cr.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN docs d ON cr.doc_id = d.doc_id
WHERE d.chembl_id = 'CHEMBL1123860'
    AND cs.canonical_smiles IS NOT NULL
ORDER BY md.chembl_id ASC, cr.compound_name ASC, cs.canonical_smiles ASC;
