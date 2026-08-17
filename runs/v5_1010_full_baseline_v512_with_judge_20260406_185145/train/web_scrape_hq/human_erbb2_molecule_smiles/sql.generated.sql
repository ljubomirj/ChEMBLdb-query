SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary m ON m.molregno = act.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE a.assay_organism = 'Homo sapiens'
  AND td.chembl_id = 'CHEMBL1824'
  AND act.type = 'IC50';
