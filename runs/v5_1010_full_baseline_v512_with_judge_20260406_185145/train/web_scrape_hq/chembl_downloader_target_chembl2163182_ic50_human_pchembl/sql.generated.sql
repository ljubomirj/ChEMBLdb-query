SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       act.standard_type,
       act.pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND td.tid = 2163182
  AND act.activity_type = 'IC50'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
LIMIT 1000
ORDER BY molecule_chembl_id, assay_chembl_id
