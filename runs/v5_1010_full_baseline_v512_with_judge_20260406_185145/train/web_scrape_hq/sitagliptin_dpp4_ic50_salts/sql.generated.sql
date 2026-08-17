SELECT DISTINCT
  child.chembl_id AS compound_chembl_id,
  cs.canonical_smiles,
  r.compound_key AS compound_key,
  d.pubmed_id AS pubmed_id_or_doi,
  ass.description AS assay_description,
  a.standard_type,
  a.standard_relation,
  a.standard_value,
  a.standard_units,
  a.activity_comment,
  t.chembl_id AS target_chembl_id,
  t.pref_name AS target_name,
  t.organism AS target_organism
FROM molecule_dictionary parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
JOIN molecule_dictionary child ON child.molregno = mh.molregno
JOIN compound_records r ON r.molregno = child.molregno
JOIN docs d ON r.doc_id = d.doc_id
JOIN activities a ON r.record_id = a.record_id
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary t ON ass.tid = t.tid
LEFT JOIN compound_structures cs ON cs.molregno = child.molregno
WHERE parent.chembl_id = 'CHEMBL1422'
  AND t.chembl_id = 'CHEMBL284'
  AND a.standard_type = 'IC50'
  AND a.bao_endpoint = 'BAO_0000190'
  AND a.uo_units = 'nM';
