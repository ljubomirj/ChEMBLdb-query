SELECT DISTINCT m.chembl_id AS molecule_chembl_id, m.pref_name AS molecule_name, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
LEFT JOIN compound_records cr ON m.molregno = cr.molregno
LEFT JOIN docs d ON cr.doc_id = d.doc_id
LEFT JOIN activities act ON cr.record_id = act.record_id
LEFT JOIN assays a ON act.assay_id = a.assay_id
LEFT JOIN target_dictionary td ON a.tid = td.tid
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE d.chembl_id = 'CHEMBL1123873'
  AND cs.canonical_smiles IS NOT NULL
ORDER BY m.chembl_id, m.pref_name, cs.canonical_smiles;
