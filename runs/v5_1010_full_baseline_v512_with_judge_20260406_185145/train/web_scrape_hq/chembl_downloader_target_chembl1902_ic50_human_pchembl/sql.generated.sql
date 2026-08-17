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
JOIN compound_structures cs ON act.molregno = cs.molregno
JOIN molecule_dictionary md ON cs.molregno = md.molregno
WHERE td.tid = 1902
  AND a.assay_type = 'B'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.tax_id = 9606
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
