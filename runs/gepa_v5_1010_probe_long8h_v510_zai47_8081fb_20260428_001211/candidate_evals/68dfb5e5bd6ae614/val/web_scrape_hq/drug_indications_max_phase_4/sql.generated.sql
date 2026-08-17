SELECT
  md.chembl_id,
  md.pref_name,
  di.mesh_id,
  di.mesh_heading,
  di.efo_id AS indication_curie,
  di.efo_term AS indication_label,
  di.max_phase_for_ind
FROM drug_indication di
JOIN molecule_dictionary md ON di.molregno = md.molregno
WHERE di.max_phase_for_ind = 4
ORDER BY
  md.chembl_id,
  md.pref_name,
  di.mesh_id,
  di.mesh_heading,
  di.efo_id,
  di.efo_term,
  di.max_phase_for_ind
