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
JOIN compound_structures cs ON a.molregno = cs.molregno
JOIN molecule_dictionary md ON cs.molregno = md.molregno
WHERE a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND a.type = 'IC50'
  AND td.chembl_id = 'CHEMBL1250411'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.tax_id = 9606
  AND a2.assay_type = 'B'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
