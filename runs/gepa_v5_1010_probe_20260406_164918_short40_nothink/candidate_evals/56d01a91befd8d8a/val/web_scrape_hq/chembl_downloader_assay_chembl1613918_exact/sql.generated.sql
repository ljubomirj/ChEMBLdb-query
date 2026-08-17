SELECT DISTINCT cs.canonical_smiles AS canonical_smiles, m.chembl_id AS chembl_id, a.standard_type AS standard_type, a.standard_relation AS standard_relation, a.standard_value AS standard_value, a.standard_units AS standard_units
FROM activities a
JOIN compound_structures cs ON a.molregno = cs.molregno
JOIN molecule_dictionary m ON a.molregno = m.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
WHERE ass.chembl_id = 'CHEMBL1613918'
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
ORDER BY cs.canonical_smiles, m.chembl_id, a.standard_type, a.standard_relation, a.standard_value, a.standard_units;
