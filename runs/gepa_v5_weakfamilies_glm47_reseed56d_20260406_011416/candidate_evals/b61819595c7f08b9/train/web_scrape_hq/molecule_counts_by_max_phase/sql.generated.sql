SELECT max_phase, COUNT(*) AS molecule_count FROM molecule_dictionary GROUP BY max_phase ORDER BY max_phase, molecule_count
