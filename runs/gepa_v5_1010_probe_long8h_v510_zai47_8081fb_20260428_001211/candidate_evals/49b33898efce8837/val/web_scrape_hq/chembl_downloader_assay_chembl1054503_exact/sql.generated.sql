SELECT
  cs.canonical_smiles,
  md.chembl_id,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units
FROM activities a
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON a.molregno = cs.molregno
WHERE a.assay_id = (SELECT assay_id FROM assays WHERE chembl_id = 'CHEMBL1054503')
  AND a.standard_value IS NOT NULL
  AND a.standard_relation = '='
ORDER BY cs.canonical_smiles, md.chembl_id, a.standard_type, a.standard_relation, a.standard_value, a.standard_units
