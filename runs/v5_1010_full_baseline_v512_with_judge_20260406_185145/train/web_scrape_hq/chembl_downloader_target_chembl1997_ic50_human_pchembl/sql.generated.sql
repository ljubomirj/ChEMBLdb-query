SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN compound_records cr ON a.record_id = cr.record_id
JOIN molecule_dictionary md ON cr.molregno = md.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
WHERE a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
  AND a.bao_endpoint = 'IC50'
  AND ass.assay_organism = 'Homo sapiens'
  AND td.tid = 1997
  AND a.standard_type = 'IC50'
  AND a.standard_value IS NOT NULL
  AND a.standard_units IS NOT NULL
LIMIT 1000
