SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles
FROM molecule_dictionary m
JOIN activities a ON a.molregno = m.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary t ON ass.tid = t.tid
JOIN target_type tt ON t.target_type = tt.target_type
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE tt.target_type = 'PROTEIN' AND t.organism = 'Homo sapiens';
