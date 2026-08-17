SELECT DISTINCT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       cs.canonical_smiles AS canonical_smiles,
       m.max_phase AS max_phase,
       di.mesh_heading AS mesh_heading,
       m.first_approval AS first_approval
FROM molecule_dictionary m
JOIN drug_indication di ON m.molregno = di.molregno
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE m.therapeutic_flag = 1
  AND m.oral = 1
  AND m.black_box_warning = 0
  AND m.withdrawn_flag = 0
ORDER BY m.first_approval DESC;
