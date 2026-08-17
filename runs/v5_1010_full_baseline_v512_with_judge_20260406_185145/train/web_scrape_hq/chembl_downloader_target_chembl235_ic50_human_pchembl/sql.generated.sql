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
JOIN molecule_dictionary md ON md.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND td.tid = 235
  AND td.target_type = 'SINGLE PROTEIN'
  AND act.type = 'IC50'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
