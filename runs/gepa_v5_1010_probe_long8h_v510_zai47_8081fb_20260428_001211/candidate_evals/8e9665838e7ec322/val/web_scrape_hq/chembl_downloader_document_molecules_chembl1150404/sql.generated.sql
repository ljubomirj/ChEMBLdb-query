SELECT
  md.chembl_id AS molecule_chembl_id,
  md.pref_name AS molecule_name,
  md.max_phase,
  md.molecule_type,
  cs.canonical_smiles
FROM molecule_dictionary md
INNER JOIN compound_records cr ON md.molregno = cr.molregno
INNER JOIN docs d ON cr.doc_id = d.doc_id
INNER JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE d.chembl_id = 'CHEMBL1150404'
ORDER BY md.chembl_id ASC
