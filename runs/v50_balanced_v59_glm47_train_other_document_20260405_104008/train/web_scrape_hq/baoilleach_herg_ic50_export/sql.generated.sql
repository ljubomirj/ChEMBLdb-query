SELECT
  act.activity_id,
  a.chembl_id AS assay_chembl_id,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.standard_type,
  md.chembl_id AS molecule_chembl_id
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN molecule_dictionary md ON act.molregno = md.molregno
WHERE a.tid = 165
  AND act.standard_type = 'IC50'
ORDER BY act.activity_id, a.chembl_id, md.chembl_id
