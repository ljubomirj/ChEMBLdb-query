SELECT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.bao_endpoint = 'IC50'
  AND a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND td.chembl_id = 'CHEMBL2940'
  AND td.organism = 'Homo sapiens'
ORDER BY md.chembl_id,
         ass.chembl_id
LIMIT 1000;
