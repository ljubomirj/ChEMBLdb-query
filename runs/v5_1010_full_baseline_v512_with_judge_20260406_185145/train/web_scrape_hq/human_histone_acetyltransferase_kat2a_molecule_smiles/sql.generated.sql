SELECT DISTINCT md.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary md
JOIN compound_records cr ON md.molregno = cr.molregno
JOIN activities act ON cr.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE td.pref_name = 'human histone acetyltransferase KAT2A'
  AND a.assay_organism = 'Homo sapiens'
  AND a.assay_type = 'B'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
ORDER BY molecule_chembl_id
LIMIT 1000;
