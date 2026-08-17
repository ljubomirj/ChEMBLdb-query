SELECT DISTINCT
  md.chembl_id AS chembl_id,
  md.pref_name AS pref_name,
  cs.canonical_smiles AS canonical_smiles,
  md.max_phase AS max_phase,
  di.mesh_heading AS mesh_heading,
  md.first_approval AS first_approval
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN drug_indication di ON md.molregno = di.molregno
WHERE md.max_phase = 4
ORDER BY md.first_approval DESC;
