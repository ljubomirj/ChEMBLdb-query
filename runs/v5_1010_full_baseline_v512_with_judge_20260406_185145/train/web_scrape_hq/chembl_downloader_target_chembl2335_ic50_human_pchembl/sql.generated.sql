SELECT DISTINCT assay_chembl_id, target_type, tax_id, canonical_smiles, molecule_chembl_id, standard_type, pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.bao_endpoint = 'IC50'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND td.chembl_id = 'CHEMBL2335'
  AND td.organism = 'Homo sapiens'
  AND td.target_type = 'SINGLE PROTEIN'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
