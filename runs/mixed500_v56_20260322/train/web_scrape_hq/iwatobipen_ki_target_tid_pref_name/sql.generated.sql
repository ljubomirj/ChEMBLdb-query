SELECT DISTINCT
  td.tid AS target_tid,
  td.pref_name AS target_name
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE act.standard_type = 'Ki'
  AND act.standard_relation = '='
ORDER BY td.tid, td.pref_name
