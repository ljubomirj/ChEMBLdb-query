SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno AND act.standard_type = 'IC50'
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE t.pref_name = 'Sialic acid‑binding Ig‑like lectin 9' AND t.tax_id = 9606
ORDER BY compound_chembl_id;
