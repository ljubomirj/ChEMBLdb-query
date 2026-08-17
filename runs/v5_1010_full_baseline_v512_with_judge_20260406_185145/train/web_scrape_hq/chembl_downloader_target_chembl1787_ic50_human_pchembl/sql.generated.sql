SELECT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       act.standard_type,
       act.pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND td.chembl_id = 'CHEMBL1787'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.tax_id = 9606
  AND a.assay_type = 'B'
  AND a.assay_organism = 'Homo sapiens'
  AND act.type = 'IC50'
ORDER BY molecule_chembl_id,
         assay_chembl_id
LIMIT 1000;
