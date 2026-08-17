SELECT DISTINCT a.chembl_id AS assay_chembl_id,
       t.target_type,
       t.tax_id,
       cs.canonical_smiles,
       md.chembl_id AS molecule_chembl_id,
       a.standard_type,
       a.pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN compound_structures cs ON act.molregno = cs.molregno
JOIN molecule_dictionary md ON cs.molregno = md.molregno
WHERE act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND t.tid = 1743122
  AND t.target_type = 'SINGLE PROTEIN'
  AND a.assay_organism = 'Homo sapiens'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000;
