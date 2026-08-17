SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.tid = 1963
  AND td.target_type = 'SINGLE PROTEIN'
  AND a.assay_type = 'B'
ORDER BY molecule_chembl_id;
