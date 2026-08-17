SELECT DISTINCT md.chembl_id AS compound_chembl_id, cs.canonical_smiles
FROM molecule_dictionary md
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE td.chembl_id = 'CHEMBL218'
  AND a.assay_organism = 'Homo sapiens'
ORDER BY md.chembl_id
