SELECT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       act.standard_type,
       act.pchembl_value
FROM activities act
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
LEFT JOIN compound_structures cs ON cs.molregno = act.molregno
JOIN molecule_dictionary md ON md.molregno = act.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND td.tid = 3371
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
