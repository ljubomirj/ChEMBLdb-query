SELECT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       cs.canonical_smiles AS canonical_smiles,
       m.max_phase AS max_phase,
       dm.mechanism_of_action AS mechanism_of_action,
       at.action_type AS action_type,
       td.chembl_id AS target_chembl_id,
       td.pref_name AS target_name
FROM molecule_dictionary m
JOIN drug_mechanism dm ON dm.molregno = m.molregno
JOIN action_type at ON at.action_type = dm.action_type
JOIN assays a ON a.assay_id = dm.record_id
JOIN target_dictionary td ON td.tid = a.tid
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE m.therapeutic_flag = 1
  AND at.action_type = 'POSITIVE ALLOSTERIC MODULATOR'
  AND m.availability_type = 1
ORDER BY m.chembl_id, m.pref_name, cs.canonical_smiles, m.max_phase, dm.mechanism_of_action, at.action_type, td.chembl_id, td.pref_name;
