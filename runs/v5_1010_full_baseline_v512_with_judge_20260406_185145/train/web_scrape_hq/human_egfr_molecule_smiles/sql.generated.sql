SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE a.assay_organism = 'Homo sapiens' AND td.chembl_id = 'CHEMBL203';
