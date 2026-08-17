SELECT DISTINCT td.pref_name AS target_description
FROM assays a
JOIN target_dictionary td ON td.tid = a.tid
JOIN activities act ON act.assay_id = a.assay_id
WHERE td.organism = 'Caenorhabditis elegans'
ORDER BY target_description
