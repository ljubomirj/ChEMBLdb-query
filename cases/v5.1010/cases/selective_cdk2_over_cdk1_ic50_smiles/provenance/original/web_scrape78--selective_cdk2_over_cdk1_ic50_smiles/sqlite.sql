SELECT DISTINCT md.chembl_id AS compound_chembl_id,
       cs.canonical_smiles,
       act1.standard_value AS ic50_target1_nM,
       act2.standard_value AS ic50_target2_nM
FROM activities act1
JOIN assays a1 ON act1.assay_id = a1.assay_id
JOIN target_dictionary td1 ON a1.tid = td1.tid
JOIN molecule_dictionary md ON act1.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN activities act2 ON act2.molregno = md.molregno
JOIN assays a2 ON act2.assay_id = a2.assay_id
JOIN target_dictionary td2 ON a2.tid = td2.tid
WHERE td1.chembl_id = 'CHEMBL211'
  AND td2.chembl_id = 'CHEMBL240'
  AND act1.standard_type = 'IC50' AND act1.standard_units = 'nM' AND act1.standard_relation = '='
  AND act2.standard_type = 'IC50' AND act2.standard_units = 'nM' AND act2.standard_relation = '='
  AND act1.standard_value IS NOT NULL AND act2.standard_value IS NOT NULL
  AND act1.standard_value < 1000 AND act2.standard_value > 10000
