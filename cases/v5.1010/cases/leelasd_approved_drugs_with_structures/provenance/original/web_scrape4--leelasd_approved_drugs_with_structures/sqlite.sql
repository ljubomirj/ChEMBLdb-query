SELECT DISTINCT md.chembl_id AS molecule_chembl_id,
       md.pref_name,
       cs.canonical_smiles,
       md.max_phase,
       md.first_approval
FROM molecule_dictionary AS md
JOIN compound_records AS cr ON md.molregno = cr.molregno
LEFT JOIN compound_structures AS cs ON cs.molregno = md.molregno
WHERE md.max_phase IN (3, 4)
ORDER BY md.first_approval DESC, md.chembl_id;
