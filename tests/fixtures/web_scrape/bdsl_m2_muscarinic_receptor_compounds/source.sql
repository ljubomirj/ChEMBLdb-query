SELECT DISTINCT
  m.chembl_id,
  s.canonical_smiles,
  r.compound_key,
  d.pubmed_id,
  a.description,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment,
  t.chembl_id,
  t.pref_name
FROM molecule_dictionary m
JOIN compound_structures s ON s.molregno = m.molregno
JOIN compound_records r ON m.molregno = r.molregno
JOIN docs d ON r.doc_id = d.doc_id
JOIN activities act ON r.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN target_components tc ON t.tid = tc.tid
JOIN component_sequences cs ON tc.component_id = cs.component_id
WHERE cs.accession = 'P08172';
