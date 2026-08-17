SELECT m.chembl_id AS chembl_id,
       m.pref_name AS pref_name,
       cs.canonical_smiles AS canonical_smiles,
       m.max_phase AS max_phase,
       dm.mechanism_of_action AS mechanism_of_action,
       at.action_type AS action_type,
       td.chembl_id AS target_chembl_id,
       td.pref_name AS target_name
FROM molecule_dictionary m
JOIN drug_mechanism dm ON dm.molregno = m.molregno AND dm.action_type = 'BLOCKER'
JOIN action_type at ON at.action_type = dm.action_type
JOIN assays a ON a.tid = dm.tid
JOIN target_dictionary td ON td.tid = a.tid
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
ORDER BY m.chembl_id, m.pref_name, cs.canonical_smiles, m.max_phase, dm.mechanism_of_action, at.action_type, td.chembl_id, td.pref_name;
