SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON act.molregno = cs.molregno
JOIN molecule_dictionary md ON cs.molregno = md.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND td.chembl_id = 'CHEMBL1914272'
  AND td.target_type = 'SINGLE PROTEIN'
  AND a.assay_organism = 'Homo sapiens'
  AND act.bao_endpoint = 'IC50'
ORDER BY molecule_chembl_id,
         assay_chembl_id
LIMIT 1000;
