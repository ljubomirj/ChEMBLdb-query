SELECT DISTINCT
  cs.canonical_smiles AS canonical_smiles,
  sub.pref_name AS substrate_compound_name,
  parent.pref_name AS parent_compound_name,
  met.met_conversion AS met_conversion,
  met.pathway_key AS pathway_key,
  td.organism AS organism,
  met.enzyme_name AS enzyme_name
FROM metabolism met
JOIN compound_structures cs ON cs.molregno = met.substrate_record_id
JOIN molecule_dictionary sub ON sub.molregno = met.substrate_record_id
JOIN molecule_dictionary parent ON parent.molregno = met.metabolite_record_id
JOIN compound_records cr ON cr.molregno = sub.molregno
JOIN docs d ON d.doc_id = cr.doc_id
JOIN assays a ON a.assay_id = met.assay_id
JOIN target_dictionary td ON td.tid = a.tid
WHERE td.organism = 'Canis lupus familiaris'
LIMIT 200
