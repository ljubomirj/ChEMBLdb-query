SELECT
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.chembl_id = 'CHEMBL1613842'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '='
ORDER BY cs.canonical_smiles, md.chembl_id, act.standard_type, act.standard_relation, act.standard_value, act.standard_units
