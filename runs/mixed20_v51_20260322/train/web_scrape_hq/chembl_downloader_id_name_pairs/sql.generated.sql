SELECT m.chembl_id, m.pref_name FROM molecule_dictionary m JOIN compound_structures s ON s.molregno = m.molregno WHERE m.pref_name IS NOT NULL ORDER BY m.chembl_id, m.pref_name
