SELECT DISTINCT td.pref_name AS target_description
FROM assays a
JOIN target_dictionary td ON a.tid = td.tid
WHERE a.assay_organism = 'Caenorhabditis elegans'
  AND EXISTS (
    SELECT 1
    FROM activities act
    WHERE act.assay_id = a.assay_id
  )
ORDER BY td.pref_name ASC
