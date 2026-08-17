SELECT cs.canonical_smiles AS canonical_smiles,
       m.chembl_id AS chembl_id,
       act.standard_type AS standard_type,
       act.standard_relation AS standard_relation,
       act.standard_value AS standard_value,
       act.standard_units AS standard_units
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary m ON act.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE a.chembl_id = 'CHEMBL1613886'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '='
ORDER BY cs.canonical_smiles,
         m.chembl_id,
         act.standard_type,
         act.standard_relation,
         act.standard_value,
         act.standard_units;
