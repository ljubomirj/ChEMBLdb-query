SELECT DISTINCT
  activities.activity_id,
  molecule_dictionary.chembl_id AS molecule_chembl_id,
  target_dictionary.chembl_id AS target_chembl_id,
  target_dictionary.pref_name AS target_name,
  activities.standard_type,
  activities.standard_value,
  activities.standard_units
FROM activities
JOIN assays ON assays.assay_id = activities.assay_id
JOIN target_dictionary ON target_dictionary.tid = assays.tid
JOIN molecule_dictionary ON molecule_dictionary.molregno = activities.molregno
WHERE target_dictionary.organism = 'Homo sapiens'
  AND target_dictionary.target_type = 'SINGLE PROTEIN'
  AND activities.standard_units = 'nM'
  AND activities.standard_type IN ('EC50', 'IC50', 'AC50')
  AND activities.standard_value < 50
ORDER BY activities.activity_id
LIMIT 200
