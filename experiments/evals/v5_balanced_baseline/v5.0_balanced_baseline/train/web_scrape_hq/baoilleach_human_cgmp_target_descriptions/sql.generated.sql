SELECT DISTINCT td.pref_name AS target_description FROM target_dictionary td WHERE td.organism = 'Homo sapiens' AND td.pref_name LIKE 'cGMP%' ORDER BY target_description
