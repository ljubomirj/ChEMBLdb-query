SELECT DISTINCT md.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN molecule_dictionary md ON cr.molregno = md.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.assay_organism = 'Homo sapiens' AND td.pref_name = 'Cytochrome P450 3A4'
ORDER BY molecule_chembl_id;
