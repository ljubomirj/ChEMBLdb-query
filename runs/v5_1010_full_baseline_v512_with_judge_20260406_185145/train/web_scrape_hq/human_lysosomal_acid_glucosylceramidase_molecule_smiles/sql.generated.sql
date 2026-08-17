SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON m.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.tid = 2179
  AND td.target_type = 'PROTEIN'
  AND td.pref_name = 'human lysosomal acid glucosylceramidase'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND act.pchembl_value IS NOT NULL
  AND act.pchembl_value <= 6
ORDER BY molecule_chembl_id ASC
LIMIT 100
