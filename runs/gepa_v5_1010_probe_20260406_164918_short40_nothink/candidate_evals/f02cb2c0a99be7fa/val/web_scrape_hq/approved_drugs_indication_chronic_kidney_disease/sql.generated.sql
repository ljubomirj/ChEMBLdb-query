SELECT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       cs.canonical_smiles AS canonical_smiles,
       td.chembl_id AS indication_curie,
       td.pref_name AS indication_label,
       m.max_phase AS max_phase_for_ind
FROM molecule_dictionary m
JOIN drug_indication di ON m.molregno = di.molregno
JOIN target_dictionary td ON di.tid = td.tid
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.target_type = 'DISEASE'
  AND td.pref_name = 'Chronic kidney disease'
  AND m.therapeutic_flag = 1
ORDER BY m.chembl_id, m.pref_name, cs.canonical_smiles, td.chembl_id, td.pref_name, m.max_phase_for_ind;
