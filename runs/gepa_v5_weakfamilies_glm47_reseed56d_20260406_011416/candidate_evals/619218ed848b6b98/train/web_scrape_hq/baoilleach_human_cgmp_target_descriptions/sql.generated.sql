SELECT DISTINCT pref_name AS target_description
FROM target_dictionary
WHERE organism = 'Homo sapiens'
  AND pref_name LIKE 'cGMP%'
ORDER BY pref_name
