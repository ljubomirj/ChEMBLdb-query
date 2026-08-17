SELECT
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
FROM compound_structures cs
JOIN molecule_dictionary md ON md.molregno = cs.molregno
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON act.assay_id = a.assay_id
WHERE a.chembl_id = 'CHEMBL3885862'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
ORDER BY cs.canonical_smiles, md.chembl_id, act.standard_type, act.standard_relation, act.standard_value, act.standard_units
