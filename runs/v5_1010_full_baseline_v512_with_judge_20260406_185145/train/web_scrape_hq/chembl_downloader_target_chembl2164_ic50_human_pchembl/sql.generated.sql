SELECT a.chembl_id AS assay_chembl_id,
       t.target_type,
       t.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       act.standard_type,
       act.pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND a.assay_organism = 'Homo sapiens'
  AND t.tid = 2164
  AND t.target_type = 'SINGLE PROTEIN'
  AND act.activity_type = 'IC50'
ORDER BY molecule_chembl_id ASC,
         assay_chembl_id ASC,
         canonical_smiles ASC,
         target_type ASC,
         tax_id ASC,
         standard_type ASC,
         pchembl_value ASC
LIMIT 1000;
