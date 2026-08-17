SELECT DISTINCT
  a.chembl_id AS assay_chembl_id,
  td.target_type,
  td.tax_id,
  cs.canonical_smiles AS canonical_smiles,
  md.chembl_id AS molecule_chembl_id,
  act.standard_type,
  act.pchembl_value AS pchembl_value
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
LEFT JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE td.chembl_id = 'CHEMBL1293289'
  AND a.assay_organism = 'Homo sapiens'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
  AND act.pchembl_value IS NOT NULL
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND act.standard_flag = 1
  AND a.assay_type = 'B'
  AND a.assay_tax_id = 9606
  AND a.assay_strain IS NOT NULL
  AND a.assay_cell_type IS NOT NULL
  AND a.assay_subcellular_fraction IS NOT NULL
  AND a.bao_format IS NOT NULL
  AND a.tissue_id IS NOT NULL
  AND a.variant_id IS NOT NULL
  AND a.aidx IS NOT NULL
  AND a.assay_group IS NOT NULL
  AND a.relationship_type IS NOT NULL
  AND a.confidence_score IS NOT NULL
  AND a.curated_by IS NOT NULL
  AND a.src_id IS NOT NULL
  AND a.src_assay_id IS NOT NULL
  AND a.chembl_id IS NOT NULL
  AND a.doc_id IS NOT NULL
  AND act.doc_id IS NOT NULL
  AND act.record_id IS NOT NULL
  AND act.activity_id IS NOT NULL
  AND act.activity_comment IS NOT NULL
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000
