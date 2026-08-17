SELECT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       di.mesh_id AS mesh_id,
       di.mesh_heading AS mesh_heading,
       di.mesh_id AS indication_curie,
       di.mesh_heading AS indication_label,
       di.max_phase_for_ind AS max_phase_for_ind
FROM molecule_dictionary m
JOIN drug_indication di ON m.molregno = di.molregno
WHERE di.max_phase_for_ind = 3
  AND m.therapeutic_flag = 1
ORDER BY m.chembl_id,
         m.pref_name,
         di.mesh_id,
         di.mesh_heading,
         di.mesh_id,
         di.mesh_heading,
         di.max_phase_for_ind;
