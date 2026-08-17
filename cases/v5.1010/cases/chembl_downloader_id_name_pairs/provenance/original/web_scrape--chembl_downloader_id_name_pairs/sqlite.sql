SELECT md.chembl_id, md.pref_name
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE md.pref_name IS NOT NULL;
