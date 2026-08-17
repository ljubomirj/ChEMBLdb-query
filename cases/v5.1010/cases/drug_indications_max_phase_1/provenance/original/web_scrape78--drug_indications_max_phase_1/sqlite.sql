SELECT md.chembl_id,
       md.pref_name,
       di.mesh_id,
       di.mesh_heading,
       di.efo_id AS indication_curie,
       di.efo_term AS indication_label,
       di.max_phase_for_ind
FROM molecule_dictionary md
JOIN drug_indication di ON md.molregno = di.molregno
WHERE md.max_phase = 4
  AND di.max_phase_for_ind = 1
