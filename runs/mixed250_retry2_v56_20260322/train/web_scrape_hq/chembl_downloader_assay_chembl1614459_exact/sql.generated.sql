SELECT
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
FROM activities act
JOIN molecule_dictionary md ON md.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE act.assay_id = (SELECT assay_id FROM assays WHERE chembl_id = 'CHEMBL1614459')
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
ORDER BY
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units
