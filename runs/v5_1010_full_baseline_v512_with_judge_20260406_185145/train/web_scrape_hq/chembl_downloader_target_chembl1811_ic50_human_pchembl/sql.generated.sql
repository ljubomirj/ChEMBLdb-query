SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays ON a.assay_id = assays.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON a.molregno = cs.molregno
JOIN molecule_dictionary md ON cs.molregno = md.molregno
WHERE a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND a.activity_type = 'IC50'
  AND a.tid IN (SELECT tid
                  FROM target_dictionary
                  WHERE chembl_id = 'CHEMBL1811')
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
