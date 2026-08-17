SELECT DISTINCT
  m.chembl_id,
  m.pref_name,
  s.canonical_smiles,
  m.max_phase,
  di.mesh_heading,
  m.first_approval
FROM molecule_dictionary m
INNER JOIN drug_indication di ON m.molregno = di.molregno
LEFT JOIN compound_structures s ON m.molregno = s.molregno
WHERE m.max_phase = 4
ORDER BY m.first_approval DESC, m.chembl_id, m.pref_name, s.canonical_smiles, m.max_phase, di.mesh_heading
