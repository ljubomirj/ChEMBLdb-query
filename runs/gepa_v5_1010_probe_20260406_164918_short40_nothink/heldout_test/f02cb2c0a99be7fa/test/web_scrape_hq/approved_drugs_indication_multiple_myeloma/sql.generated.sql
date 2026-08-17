SELECT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       cs.canonical_smiles AS canonical_smiles,
       di.mesh_id AS indication_curie,
       di.mesh_heading AS indication_label,
       di.max_phase_for_ind AS max_phase_for_ind
FROM molecule_dictionary m
JOIN drug_indication di ON di.molregno = m.molregno
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE di.mesh_heading = 'Multiple Myeloma'
  AND m.therapeutic_flag = 1
ORDER BY m.chembl_id, m.pref_name, cs.canonical_smiles, di.mesh_id, di.mesh_heading, di.max_phase_for_ind;
