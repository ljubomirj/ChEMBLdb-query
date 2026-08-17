SELECT DISTINCT td.pref_name AS target_description
FROM assays a
JOIN target_dictionary td ON a.tid = td.tid
JOIN activities act ON a.assay_id = act.assay_id
WHERE a.assay_organism = 'Caenorhabditis elegans'
ORDER BY td.pref_name
