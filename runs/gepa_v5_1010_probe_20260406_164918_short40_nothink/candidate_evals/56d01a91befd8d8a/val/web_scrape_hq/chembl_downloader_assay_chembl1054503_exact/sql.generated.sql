SELECT cs.canonical_smiles,
       m.chembl_id AS chembl_id,
       act.standard_type,
       act.standard_relation,
       act.standard_value,
       act.standard_units
FROM activities act
INNER JOIN assays a ON act.assay_id = a.assay_id
INNER JOIN compound_records cr ON act.record_id = cr.record_id
INNER JOIN molecule_dictionary m ON cr.molregno = m.molregno
INNER JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE a.chembl_id = 'CHEMBL1054503'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '=';
