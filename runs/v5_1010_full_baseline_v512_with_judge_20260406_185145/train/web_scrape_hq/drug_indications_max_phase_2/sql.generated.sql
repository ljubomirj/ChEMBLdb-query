SELECT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       di.mesh_id AS mesh_id,
       di.mesh_heading AS mesh_heading,
       di.mesh_id AS indication_curie,
       di.mesh_heading AS indication_label,
       di.max_phase_for_ind AS max_phase_for_ind
FROM molecule_dictionary m
JOIN drug_indication di ON m.molregno = di.molregno
WHERE m.max_phase_for_ind = 4
  AND di.max_phase_for_ind = 2;
