SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.pref_name = 'Human Interleukin-1 receptor-associated kinase 4'
ORDER BY m.chembl_id;
