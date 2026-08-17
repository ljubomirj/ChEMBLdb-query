SELECT DISTINCT
  cs.canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units
FROM activities a
JOIN compound_structures cs ON cs.molregno = a.molregno
JOIN molecule_dictionary md ON md.molregno = a.molregno
JOIN assays a2 ON a.assay_id = a2.assay_id
JOIN target_dictionary td ON a2.tid = td.tid
WHERE a.assay_id = 'CHEMBL1217643'
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
  AND a.standard_relation IS NOT NULL
ORDER BY cs.canonical_smiles,
         md.chembl_id,
         a.standard_type,
         a.standard_relation,
         a.standard_value,
         a.standard_units;
