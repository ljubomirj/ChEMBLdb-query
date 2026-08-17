SELECT
  cs.canonical_smiles,
  md.chembl_id,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units
FROM assays ass
JOIN activities a ON a.assay_id = ass.assay_id
JOIN molecule_dictionary md ON md.molregno = a.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE ass.chembl_id = 'CHEMBL1613918'
  AND a.standard_value IS NOT NULL
  AND a.standard_relation = '='
ORDER BY cs.canonical_smiles, md.chembl_id, a.standard_type, a.standard_relation, a.standard_value, a.standard_units
