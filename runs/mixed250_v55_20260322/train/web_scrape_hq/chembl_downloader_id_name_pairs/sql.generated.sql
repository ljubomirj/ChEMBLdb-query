SELECT md.chembl_id, md.pref_name FROM molecule_dictionary md INNER JOIN compound_structures cs ON cs.molregno = md.molregno WHERE md.pref_name IS NOT NULL ORDER BY md.chembl_id, md.pref_name
