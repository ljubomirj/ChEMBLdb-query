SELECT DISTINCT md.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary md
JOIN compound_records cr ON md.molregno = cr.molregno
JOIN activities act ON cr.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE td.chembl_id = 'CHEMBL3553'
  AND a.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id;
