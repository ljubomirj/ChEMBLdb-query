SELECT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       di.mesh_id AS mesh_id,
       di.mesh_heading AS indication_curie,
       di.efo_id AS indication_label,
       di.max_phase_for_ind AS max_phase_for_ind
FROM molecule_dictionary m
JOIN drug_indication di ON m.molregno = di.molregno
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
ORDER BY m.chembl_id, m.pref_name, di.mesh_id, di.mesh_heading, di.efo_id, di.max_phase_for_ind;
