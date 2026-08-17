WITH egfr_hits AS (
    SELECT DISTINCT act.molregno
    FROM activities act
    JOIN assays a ON act.assay_id = a.assay_id
    JOIN target_dictionary td ON a.tid = td.tid
    WHERE td.chembl_id = 'CHEMBL203'
      AND act.standard_type = 'IC50'
      AND act.standard_relation = '='
      AND act.standard_units = 'nM'
      AND act.standard_value < 50
),
erbb2_hits AS (
    SELECT DISTINCT act.molregno
    FROM activities act
    JOIN assays a ON act.assay_id = a.assay_id
    JOIN target_dictionary td ON a.tid = td.tid
    WHERE td.chembl_id = 'CHEMBL1824'
      AND act.standard_type = 'IC50'
      AND act.standard_relation = '='
      AND act.standard_units = 'nM'
      AND act.standard_value > 200
)
SELECT md.chembl_id AS compound_chembl_id,
       cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN egfr_hits eh ON eh.molregno = md.molregno
JOIN erbb2_hits eb ON eb.molregno = md.molregno
ORDER BY md.chembl_id, cs.canonical_smiles
