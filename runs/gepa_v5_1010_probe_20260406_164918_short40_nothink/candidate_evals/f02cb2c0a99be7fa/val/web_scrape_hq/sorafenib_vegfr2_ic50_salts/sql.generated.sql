SELECT DISTINCT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  r.compound_key AS compound_key,
  COALESCE(d.pubmed_id, d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type AS standard_type,
  act.standard_relation AS standard_relation,
  act.standard_value AS standard_value,
  act.standard_units AS standard_units,
  act.activity_comment AS activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
JOIN molecule_dictionary child ON child.molregno = mh.molregno
JOIN compound_records r ON r.molregno = child.molregno
JOIN docs d ON r.doc_id = d.doc_id
JOIN activities act ON r.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON act.tid = t.tid
LEFT JOIN compound_structures cs ON cs.molregno = child.molregno
WHERE parent.chembl_id = 'CHEMBL1336'
  AND act.standard_type = 'IC50'
  AND act.bao_endpoint = 'BAO_0000190'
  AND act.standard_units = 'nM'
  AND act.standard_relation = '='
  AND act.standard_value IS NOT NULL
  AND act.standard_value > 0
  AND act.standard_value < 100000
  AND t.pref_name = 'Vascular endothelial growth factor receptor 2';
