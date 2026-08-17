SELECT
  cs.canonical_smiles,
  md.chembl_id,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE ass.chembl_id = 'CHEMBL5732041'
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
ORDER BY
  cs.canonical_smiles,
  md.chembl_id,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units
