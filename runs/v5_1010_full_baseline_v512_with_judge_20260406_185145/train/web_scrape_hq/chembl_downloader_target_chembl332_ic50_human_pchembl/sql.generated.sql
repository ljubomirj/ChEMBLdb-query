SELECT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays a2 ON a.assay_id = a2.assay_id
JOIN target_dictionary td ON a2.tid = td.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND td.tid = 332
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.tax_id = 9606
ORDER BY molecule_chembl_id,
         assay_chembl_id
LIMIT 1000;
