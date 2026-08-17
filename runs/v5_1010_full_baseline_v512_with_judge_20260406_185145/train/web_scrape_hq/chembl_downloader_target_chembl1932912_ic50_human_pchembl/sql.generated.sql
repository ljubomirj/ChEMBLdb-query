SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       t.target_type,
       t.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays a2 ON a.assay_id = a2.assay_id
JOIN target_dictionary t ON a2.tid = t.tid
JOIN compound_structures cs ON a.molregno = cs.molregno
JOIN molecule_dictionary md ON cs.molregno = md.molregno
WHERE a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND t.chembl_id = 'CHEMBL1932912'
  AND a2.assay_organism = 'Homo sapiens'
  AND t.target_type = 'SINGLE PROTEIN'
  AND a.type = 'IC50'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
