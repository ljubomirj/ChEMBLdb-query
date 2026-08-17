SELECT DISTINCT cs.canonical_smiles AS canonical_smiles,
       m.chembl_id AS chembl_id,
       a.standard_type AS standard_type,
       a.standard_relation AS standard_relation,
       a.standard_value AS standard_value,
       a.standard_units AS standard_units
FROM molecule_dictionary m
JOIN activities a ON m.molregno = a.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE ass.chembl_id = 'CHEMBL1614079'
  AND a.standard_value IS NOT NULL
  AND a.standard_relation = '='
ORDER BY canonical_smiles,
         chembl_id,
         standard_type,
         standard_relation,
         standard_value,
         standard_units;
