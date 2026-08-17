SELECT td.organism, COUNT(DISTINCT act.activity_id) AS ic50_count
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE act.standard_type = 'IC50' AND act.standard_units = 'nM'
GROUP BY td.organism
ORDER BY ic50_count DESC
