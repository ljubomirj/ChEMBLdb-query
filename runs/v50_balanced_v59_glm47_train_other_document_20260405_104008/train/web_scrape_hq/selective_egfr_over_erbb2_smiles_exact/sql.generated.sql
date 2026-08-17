SELECT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN activities act_a ON act_a.molregno = md.molregno
JOIN assays a_a ON act_a.assay_id = a_a.assay_id
JOIN target_dictionary td_a ON a_a.tid = td_a.tid
JOIN activities act_b ON act_b.molregno = md.molregno
JOIN assays a_b ON act_b.assay_id = a_b.assay_id
JOIN target_dictionary td_b ON a_b.tid = td_b.tid
WHERE
  td_a.chembl_id = 'CHEMBL203'
  AND act_a.standard_type = 'IC50'
  AND act_a.standard_relation = '='
  AND act_a.standard_units = 'nM'
  AND act_a.standard_value < 50
  AND td_b.chembl_id = 'CHEMBL1824'
  AND act_b.standard_type = 'IC50'
  AND act_b.standard_relation = '='
  AND act_b.standard_units = 'nM'
  AND act_b.standard_value > 200
ORDER BY
  md.chembl_id,
  cs.canonical_smiles
