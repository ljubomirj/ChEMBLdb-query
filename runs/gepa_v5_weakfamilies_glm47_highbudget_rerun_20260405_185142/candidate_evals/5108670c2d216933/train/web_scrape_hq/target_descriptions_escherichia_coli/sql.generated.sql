SELECT DISTINCT td.pref_name AS target_description
FROM assays a
JOIN target_dictionary td ON td.tid = a.tid
WHERE a.assay_organism = 'Escherichia coli'
ORDER BY td.pref_name ASC
