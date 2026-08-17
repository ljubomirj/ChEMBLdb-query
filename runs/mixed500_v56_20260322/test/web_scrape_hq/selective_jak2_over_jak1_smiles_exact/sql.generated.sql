WITH jak2_hits AS (
    SELECT DISTINCT act.molregno
    FROM activities act
    JOIN assays a ON act.assay_id = a.assay_id
    JOIN target_dictionary td ON a.tid = td.tid
    WHERE td.chembl_id = 'CHEMBL2971'
      AND act.standard_type = 'IC50'
      AND act.standard_relation = '='
      AND act.standard_units = 'nM'
      AND act.standard_value < 50
),
jak1_hits AS (
    SELECT DISTINCT act.molregno
    FROM activities act
    JOIN assays a ON act.assay_id = a.assay_id
    JOIN target_dictionary td ON a.tid = td.tid
    WHERE td.chembl_id = 'CHEMBL2835'
      AND act.standard_type = 'IC50'
      AND act.standard_relation = '='
      AND act.standard_units = 'nM'
      AND act.standard_value > 200
),
selective_molregnos AS (
    SELECT molregno FROM jak2_hits
    INTERSECT
    SELECT molregno FROM jak1_hits
)
SELECT md.chembl_id AS compound_chembl_id,
       cs.canonical_smiles
FROM selective_molregnos sm
JOIN molecule_dictionary md ON md.molregno = sm.molregno
JOIN compound_structures cs ON cs.molregno = sm.molregno
ORDER BY md.chembl_id, cs.canonical_smiles
