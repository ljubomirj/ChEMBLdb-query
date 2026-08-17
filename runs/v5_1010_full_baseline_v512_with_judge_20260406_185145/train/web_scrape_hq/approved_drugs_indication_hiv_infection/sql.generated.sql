SELECT
  m.chembl_id,
  m.pref_name,
  cs.canonical_smiles,
  di.efo_id AS indication_curie,
  di.mesh_heading AS indication_label,
  di.max_phase_for_ind
FROM molecule_dictionary m
JOIN drug_indication di ON m.molregno = di.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE di.max_phase_for_ind = 4
  AND di.mesh_heading = 'HIV Infection'
ORDER BY
  m.chembl_id,
  m.pref_name,
  cs.canonical_smiles,
  di.efo_id,
  di.mesh_heading,
  di.max_phase_for_ind
