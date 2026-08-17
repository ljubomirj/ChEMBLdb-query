SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       td.target_type,
       td.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities a
JOIN assays ON a.assay_id = assays.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_structures cs ON a.molregno = cs.molregno
JOIN molecule_dictionary md ON cs.molregno = md.molregno
JOIN compound_records cr ON assays.doc_id = cr.doc_id
JOIN docs d ON cr.doc_id = d.doc_id
JOIN target_dictionary t_d ON assays.tid = t_d.tid
WHERE td.tid = 1855
  AND assays.assay_type = 'B'
  AND a.standard_relation = '='
  AND a.standard_value IS NOT NULL
  AND a.pchembl_value IS NOT NULL
  AND assays.assay_organism = 'Homo sapiens'
  AND td.tax_id = 9606
ORDER BY molecule_chembl_id,
         assay_chembl_id
LIMIT 1000
