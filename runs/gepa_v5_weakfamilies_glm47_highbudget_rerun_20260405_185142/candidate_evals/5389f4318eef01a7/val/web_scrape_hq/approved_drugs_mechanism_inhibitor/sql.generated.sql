SELECT
  md.chembl_id AS chembl_id,
  md.pref_name AS pref_name,
  cs.canonical_smiles AS canonical_smiles,
  md.max_phase AS max_phase,
  dm.mechanism_of_action AS mechanism_of_action,
  dm.action_type AS action_type,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name
FROM molecule_dictionary md
JOIN drug_mechanism dm ON dm.molregno = md.molregno
JOIN target_dictionary td ON td.tid = dm.tid
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE md.max_phase = 4
  AND dm.action_type = 'INHIBITOR'
ORDER BY
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  md.max_phase,
  dm.mechanism_of_action,
  dm.action_type,
  td.chembl_id,
  td.pref_name
