SELECT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles AS canonical_smiles,
       m.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM molecule_dictionary m
JOIN activities a ON m.molregno = a.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE ass.assay_organism = 'Homo sapiens'
  AND td.chembl_id = 'CHEMBL1255131'
  AND a.type = 'IC50'
  AND a.standard_relation = '='
  AND a.pchembl_value IS NOT NULL
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
