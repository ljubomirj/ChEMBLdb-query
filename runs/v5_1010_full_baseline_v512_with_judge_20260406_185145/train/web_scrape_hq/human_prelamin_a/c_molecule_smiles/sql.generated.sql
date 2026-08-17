SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary m
JOIN activities act ON act.molregno = m.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.chembl_id = 'CHEMBL1293235'
  AND a.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id, canonical_smiles;
