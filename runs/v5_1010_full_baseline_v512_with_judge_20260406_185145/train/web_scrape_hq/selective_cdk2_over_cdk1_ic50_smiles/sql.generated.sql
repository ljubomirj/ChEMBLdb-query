SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles, a1.standard_value AS ic50_target1_nM, a2.standard_value AS ic50_target2_nM
FROM molecule_dictionary m
JOIN activities a1 ON a1.molregno = m.molregno
JOIN assays a1_assay ON a1.assay_id = a1_assay.assay_id
JOIN target_dictionary t1 ON t1.tid = a1_assay.tid
JOIN target_dictionary t2 ON t2.tid = a1_assay.tid
JOIN activities a2 ON a2.molregno = m.molregno
JOIN assays a2_assay ON a2.assay_id = a2_assay.assay_id
JOIN target_dictionary t2a ON t2a.tid = a2_assay.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE a1.standard_type = 'IC50' AND a1.standard_relation = '>' AND a1.standard_value IS NOT NULL AND a1.standard_units = 'nM' AND a1.units = 'nM' AND a1.activity_comment IS NOT NULL
  AND a1_assay.assay_type = 'B' AND a1_assay.assay_organism = 'Homo sapiens' AND t1.pref_name = 'CDK2'
  AND a2.standard_type = 'IC50' AND a2.standard_relation = '>' AND a2.standard_value IS NOT NULL AND a2.standard_units = 'nM' AND a2.units = 'nM' AND a2.activity_comment IS NOT NULL
  AND a2_assay.assay_type = 'B' AND a2_assay.assay_organism = 'Homo sapiens' AND t2a.pref_name = 'CDK1'
  AND a1.standard_value > 1000 AND a2.standard_value < 10000
ORDER BY compound_chembl_id, canonical_smiles, ic50_target1_nM, ic50_target2_nM;
