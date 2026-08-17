SELECT
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
FROM assays a
JOIN activities act ON act.assay_id = a.assay_id
JOIN molecule_dictionary md ON md.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE a.chembl_id = 'CHEMBL1217643'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_relation IS NOT NULL
ORDER BY
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
