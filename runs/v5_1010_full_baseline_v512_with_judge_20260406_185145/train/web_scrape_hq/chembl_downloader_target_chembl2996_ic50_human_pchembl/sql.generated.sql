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
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
JOIN molecule_dictionary m ON act.molregno = m.molregno
WHERE act.activity_type = 'IC50'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND t.chembl_id = 'CHEMBL2996'
  AND t.target_type = 'SINGLE PROTEIN'
  AND t.tax_id = 9606
ORDER BY m.chembl_id, a.chembl_id
LIMIT 1000;
