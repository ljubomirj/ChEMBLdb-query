SELECT
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
FROM activities act
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.assay_id = (SELECT assay_id FROM assays WHERE chembl_id = 'CHEMBL4689853')
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
ORDER BY
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
