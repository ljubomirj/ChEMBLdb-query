SELECT
  td.target_type,
  COUNT(*) AS activity_count
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
WHERE a.standard_type = 'IC50'
GROUP BY td.target_type
ORDER BY td.target_type ASC, activity_count ASC
