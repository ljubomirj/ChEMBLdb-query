SELECT DISTINCT m.chembl_id AS molecule_chembl_id, cs.canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN molecule_dictionary m ON m.molregno = cr.molregno
JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE td.chembl_id = 'CHEMBL4792'
  AND a.assay_organism = 'Homo sapiens'
  AND act.type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND m.molecule_type = 'Small molecule'
ORDER BY molecule_chembl_id;
