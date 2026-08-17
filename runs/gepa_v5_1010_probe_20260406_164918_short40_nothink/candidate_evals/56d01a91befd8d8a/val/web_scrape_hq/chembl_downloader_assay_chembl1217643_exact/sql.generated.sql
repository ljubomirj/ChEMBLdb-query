SELECT DISTINCT
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE ass.assay_id = 'CHEMBL1217643'
  AND a.standard_type IS NOT NULL
  AND a.standard_relation IS NOT NULL
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
  AND td.target_type = 'SINGLE PROTEIN'
ORDER BY cs.canonical_smiles,
         md.chembl_id,
         a.standard_type,
         a.standard_relation,
         a.standard_value,
         a.standard_units;
