SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON m.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.chembl_id = 'CHEMBL2146305'
  AND a.assay_organism = 'Homo sapiens'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_value > 0
  AND act.standard_units = 'nM'
  AND act.pchembl_value IS NOT NULL
  AND act.pchembl_value <= 9
  AND act.pchembl_value > 0
ORDER BY molecule_chembl_id, canonical_smiles;
