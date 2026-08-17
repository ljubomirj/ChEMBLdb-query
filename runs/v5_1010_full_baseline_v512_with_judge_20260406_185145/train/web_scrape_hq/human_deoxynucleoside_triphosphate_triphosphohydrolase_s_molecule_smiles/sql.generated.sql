SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary m ON m.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.pref_name = 'Human deoxynucleoside triphosphate triphosphohydrolase' AND a.assay_organism = 'Homo sapiens'
ORDER BY compound_chembl_id;
