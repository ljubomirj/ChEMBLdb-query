SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN molecule_dictionary m ON cr.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE td.tid = 5990
  AND a.assay_type = 'B'
  AND a.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id;
