SELECT DISTINCT m.chembl_id AS molecule_chembl_id, m.pref_name AS molecule_name, m.max_phase, m.molecule_type, cs.canonical_smiles
FROM molecule_dictionary m
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE cs.canonical_smiles IS NOT NULL
  AND m.pref_name IS NOT NULL
ORDER BY m.chembl_id, m.pref_name;
