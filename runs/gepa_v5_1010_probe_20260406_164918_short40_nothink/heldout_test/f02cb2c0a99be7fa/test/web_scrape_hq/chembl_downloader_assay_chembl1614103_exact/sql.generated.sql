SELECT DISTINCT cs.canonical_smiles AS canonical_smiles, m.chembl_id AS chembl_id, act.standard_type AS standard_type, act.standard_relation AS standard_relation, act.standard_value AS standard_value, act.standard_units AS standard_units
FROM activities act
JOIN compound_structures cs ON act.molregno = cs.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN molecule_dictionary m ON act.molregno = m.molregno
WHERE a.chembl_id = 'CHEMBL1614103'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '='
ORDER BY canonical_smiles, chembl_id, standard_type, standard_relation, standard_value, standard_units
LIMIT 1000;
