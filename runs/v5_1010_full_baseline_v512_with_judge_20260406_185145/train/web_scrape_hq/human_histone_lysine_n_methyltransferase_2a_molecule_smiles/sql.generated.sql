SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON m.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.pref_name = 'Histone-lysine N-methyltransferase 2A'
  AND td.target_type = 'PROTEIN'
  AND a.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id;
