SELECT DISTINCT td.pref_name AS target_description
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE a.assay_organism = 'Caenorhabditis elegans'
ORDER BY target_description ASC;
