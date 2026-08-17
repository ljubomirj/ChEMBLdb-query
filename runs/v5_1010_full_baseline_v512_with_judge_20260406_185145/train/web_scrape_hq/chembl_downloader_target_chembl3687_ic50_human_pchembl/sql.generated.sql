SELECT a.chembl_id AS assay_chembl_id,
       t.target_type,
       t.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       act.standard_type,
       act.pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND t.chembl_id = 'CHEMBL3687'
  AND t.target_type = 'SINGLE PROTEIN'
  AND a.assay_type = 'B'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
