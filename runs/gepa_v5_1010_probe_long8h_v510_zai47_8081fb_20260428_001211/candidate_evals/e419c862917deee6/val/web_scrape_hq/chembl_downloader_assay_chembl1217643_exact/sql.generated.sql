SELECT
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units
FROM activities a
JOIN molecule_dictionary md ON md.molregno = a.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN assays ass ON ass.assay_id = a.assay_id
WHERE ass.chembl_id = 'CHEMBL1217643'
  AND a.standard_relation IS NOT NULL
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
ORDER BY cs.canonical_smiles ASC,
  md.chembl_id ASC,
  a.standard_type ASC,
  a.standard_relation ASC,
  a.standard_value ASC,
  a.standard_units ASC
