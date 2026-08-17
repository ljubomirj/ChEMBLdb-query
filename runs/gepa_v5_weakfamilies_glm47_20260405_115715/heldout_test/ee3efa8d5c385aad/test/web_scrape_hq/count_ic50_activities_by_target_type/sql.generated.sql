SELECT td.target_type, COUNT(*) AS activity_count
FROM target_dictionary td
JOIN assays a ON a.tid = td.tid
JOIN activities act ON act.assay_id = a.assay_id
WHERE act.standard_type = 'IC50'
GROUP BY td.target_type
ORDER BY td.target_type ASC, activity_count ASC
