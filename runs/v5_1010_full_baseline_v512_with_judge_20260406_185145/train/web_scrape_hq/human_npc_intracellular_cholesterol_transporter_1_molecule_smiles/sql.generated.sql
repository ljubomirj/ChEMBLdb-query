SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary m ON m.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.pref_name = 'Niemann-Pick C1 intracellular cholesterol transporter 1'
  AND a.assay_type = 'B'
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND a.tid = 1293277
LIMIT 2000
