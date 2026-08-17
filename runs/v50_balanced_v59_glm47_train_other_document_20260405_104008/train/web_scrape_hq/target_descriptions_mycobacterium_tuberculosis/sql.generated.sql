SELECT DISTINCT td.pref_name AS target_description
FROM assays a
JOIN target_dictionary td ON td.tid = a.tid
WHERE a.assay_organism = 'Mycobacterium tuberculosis'
ORDER BY target_description
