SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE t.chembl_id = 'CHEMBL5113'
  AND a.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id;
