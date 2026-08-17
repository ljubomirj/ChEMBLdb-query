SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
LEFT JOIN compound_structures cs ON cs.molregno = a.molregno
LEFT JOIN molecule_dictionary md ON md.molregno = a.molregno
WHERE a.standard_type = 'IC50'
  AND a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND ass.assay_organism = 'Homo sapiens'
  AND td.chembl_id = 'CHEMBL1783'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
