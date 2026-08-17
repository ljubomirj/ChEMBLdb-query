SELECT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN molecule_dictionary md ON a.molregno = md.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND ass.assay_organism = 'Homo sapiens'
  AND td.tid = 1908389
  AND td.target_type = 'SINGLE PROTEIN'
  AND a.activity_type = 'IC50'
ORDER BY molecule_chembl_id ASC,
         assay_chembl_id ASC,
         cs.canonical_smiles ASC,
         td.target_type ASC,
         td.tax_id ASC,
         a.standard_type ASC,
         a.pchembl_value ASC
LIMIT 1000;
