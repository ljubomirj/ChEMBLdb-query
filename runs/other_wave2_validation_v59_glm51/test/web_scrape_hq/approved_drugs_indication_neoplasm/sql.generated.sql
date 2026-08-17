SELECT
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  di.efo_id AS indication_curie,
  di.mesh_heading AS indication_label,
  di.max_phase_for_ind
FROM molecule_dictionary md
JOIN drug_indication di ON di.molregno = md.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE md.max_phase = 4
  AND di.mesh_heading LIKE '%neoplasm%'
ORDER BY
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  di.efo_id,
  di.mesh_heading,
  di.max_phase_for_ind;
