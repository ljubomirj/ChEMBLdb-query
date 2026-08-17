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
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND a2.assay_organism = 'Homo sapiens'
  AND td.tid = 2864
  AND td.target_type = 'SINGLE PROTEIN'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
