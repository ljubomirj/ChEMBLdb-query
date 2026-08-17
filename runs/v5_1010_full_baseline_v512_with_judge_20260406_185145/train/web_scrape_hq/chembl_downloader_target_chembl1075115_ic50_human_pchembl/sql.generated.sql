SELECT a.chembl_id AS assay_chembl_id,
       t.target_type,
       t.tax_id,
       cs.canonical_smiles,
       m.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
LEFT JOIN compound_structures cs ON cs.molregno = act.molregno
JOIN molecule_dictionary m ON m.molregno = act.molregno
WHERE a.assay_organism = 'Homo sapiens'
  AND t.chembl_id = 'CHEMBL1075115'
  AND t.target_type = 'SINGLE PROTEIN'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
ORDER BY molecule_chembl_id,
         assay_chembl_id
LIMIT 1000;
