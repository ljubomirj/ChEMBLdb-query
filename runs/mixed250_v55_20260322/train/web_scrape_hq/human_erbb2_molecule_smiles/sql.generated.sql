SELECT DISTINCT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.assay_organism = 'Homo sapiens'
  AND td.chembl_id = 'CHEMBL1824'
ORDER BY
  md.chembl_id,
  cs.canonical_smiles
