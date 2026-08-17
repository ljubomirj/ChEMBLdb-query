-- Compounds selective for JAK2 (CHEMBL2971) over JAK1 (CHEMBL2835)
-- Selectivity is defined as IC50 < 50 nM for JAK2 and IC50 > 200 nM for JAK1.
SELECT md.chembl_id AS compound_chembl_id,
       cs.canonical_smiles
FROM target_dictionary td
JOIN assays a ON td.tid = a.tid
JOIN activities act ON a.assay_id = act.assay_id
JOIN molecule_dictionary md ON md.molregno = act.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.standard_relation = '='
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND act.standard_value < 50
  AND td.chembl_id = 'CHEMBL2971'
INTERSECT
SELECT md.chembl_id AS compound_chembl_id,
       cs.canonical_smiles
FROM target_dictionary td
JOIN assays a ON td.tid = a.tid
JOIN activities act ON a.assay_id = act.assay_id
JOIN molecule_dictionary md ON md.molregno = act.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE act.standard_relation = '='
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND act.standard_value > 200
  AND td.chembl_id = 'CHEMBL2835';
