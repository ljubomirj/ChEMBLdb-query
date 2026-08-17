SELECT
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON act.assay_id = a.assay_id
WHERE a.chembl_id = 'CHEMBL3705960'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation IS NOT NULL
  AND act.standard_relation = '='
ORDER BY
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
