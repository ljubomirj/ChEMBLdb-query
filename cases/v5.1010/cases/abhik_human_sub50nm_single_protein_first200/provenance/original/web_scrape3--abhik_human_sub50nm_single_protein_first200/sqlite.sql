SELECT DISTINCT a.activity_id,
       md.chembl_id AS molecule_chembl_id,
       td.chembl_id AS target_chembl_id,
       td.pref_name AS target_name,
       a.standard_type,
       a.standard_value,
       a.standard_units
FROM activities AS a
JOIN assays AS ass ON a.assay_id = ass.assay_id
JOIN target_dictionary AS td ON ass.tid = td.tid
JOIN molecule_dictionary AS md ON a.molregno = md.molregno
WHERE td.organism = 'Homo sapiens'
  AND td.target_type = 'SINGLE PROTEIN'
  AND a.standard_units = 'nM'
  AND a.standard_type IN ('EC50', 'IC50', 'AC50')
  AND a.standard_value IS NOT NULL
  AND a.standard_value < 50
ORDER BY a.activity_id
LIMIT 200;
