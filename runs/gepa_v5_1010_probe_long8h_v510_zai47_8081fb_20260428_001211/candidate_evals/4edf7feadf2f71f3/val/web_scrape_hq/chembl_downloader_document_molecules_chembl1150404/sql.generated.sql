SELECT
  md.chembl_id AS molecule_chembl_id,
  md.pref_name AS molecule_name,
  md.max_phase,
  md.molecule_type,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_records cr ON cr.molregno = md.molregno
JOIN docs d ON d.doc_id = cr.doc_id
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE d.chembl_id = 'CHEMBL1150404'
ORDER BY md.chembl_id ASC
