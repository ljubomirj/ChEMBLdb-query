SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays a2 ON a.assay_id = a2.assay_id
JOIN target_dictionary td ON a2.tid = td.tid
LEFT JOIN compound_structures cs ON cs.molregno = a.molregno
LEFT JOIN molecule_dictionary md ON md.molregno = a.molregno
WHERE a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND td.chembl_id = 'CHEMBL4338'
  AND td.target_type = 'SINGLE PROTEIN'
  AND a2.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id,
         assay_chembl_id
LIMIT 1000;
