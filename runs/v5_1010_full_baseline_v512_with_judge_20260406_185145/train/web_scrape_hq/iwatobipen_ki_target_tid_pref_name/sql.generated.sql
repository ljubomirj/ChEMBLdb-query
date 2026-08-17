SELECT DISTINCT target_dictionary.tid AS target_tid, target_dictionary.pref_name AS target_name
FROM activities
JOIN assays ON activities.assay_id = assays.assay_id
JOIN target_dictionary ON activities.tid = target_dictionary.tid
WHERE activities.standard_type = 'Ki' AND activities.standard_relation = '='
GROUP BY target_dictionary.tid, target_dictionary.pref_name
ORDER BY target_dictionary.tid, target_dictionary.pref_name;
