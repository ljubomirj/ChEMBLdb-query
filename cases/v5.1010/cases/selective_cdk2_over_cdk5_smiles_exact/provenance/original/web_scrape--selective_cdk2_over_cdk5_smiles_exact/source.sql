-- Compounds selective for Human CDK2 (CHEMBL301) over Human CDK5 (CHEMBL4036)
-- Selectivity is defined as IC50 < 50 nM for CDK2 and IC50 > 200 nM for CDK5.
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
  AND td.chembl_id = 'CHEMBL301'
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
  AND td.chembl_id = 'CHEMBL4036';
