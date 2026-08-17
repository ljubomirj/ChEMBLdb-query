SELECT md.max_phase, COUNT(DISTINCT md.chembl_id) AS molecule_count
FROM molecule_dictionary md
GROUP BY md.max_phase
ORDER BY md.max_phase
