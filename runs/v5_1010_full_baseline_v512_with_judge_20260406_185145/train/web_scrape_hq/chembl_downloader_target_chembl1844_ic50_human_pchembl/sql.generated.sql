SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       t.target_type,
       t.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays ON a.assay_id = assays.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND t.tid = 1844
  AND assays.assay_organism = 'Homo sapiens'
  AND assays.assay_type = 'B'
  AND a.type = 'IC50'
ORDER BY molecule_chembl_id,
         assay_chembl_id
LIMIT 1000;
