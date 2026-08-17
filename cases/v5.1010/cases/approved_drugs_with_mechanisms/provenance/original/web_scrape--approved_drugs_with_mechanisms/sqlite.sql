SELECT DISTINCT
  md.chembl_id AS chembl_id,
  md.pref_name AS pref_name,
  cs.canonical_smiles AS canonical_smiles,
  md.max_phase AS max_phase,
  dm.mechanism_of_action AS mechanism_of_action,
  dm.action_type AS action_type,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN drug_mechanism dm ON md.molregno = dm.molregno
LEFT JOIN target_dictionary td ON dm.tid = td.tid
WHERE md.max_phase = 4;
