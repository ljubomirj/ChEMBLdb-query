SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN compound_records cr ON m.molregno = cr.molregno
JOIN activities act ON cr.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.pref_name = 'histone deacetylase 1' AND a.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id;
