SELECT
    md.chembl_id AS molecule_chembl_id,
    md.pref_name AS molecule_name,
    md.max_phase AS max_phase,
    md.molecule_type AS molecule_type,
    cs.canonical_smiles AS canonical_smiles
FROM docs d
JOIN compound_records cr ON cr.doc_id = d.doc_id
JOIN molecule_dictionary md ON cr.molregno = md.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE d.chembl_id = 'CHEMBL1140846'
ORDER BY md.chembl_id