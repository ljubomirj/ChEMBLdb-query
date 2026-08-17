SELECT DISTINCT
  cs.canonical_smiles AS canonical_smiles,
  sub.pref_name AS substrate_compound_name,
  parent.pref_name AS parent_compound_name,
  met.met_conversion AS met_conversion,
  met.pathway_key AS pathway_key,
  met.organism AS organism,
  td.pref_name AS enzyme_name
FROM metabolism met
JOIN compound_records cr ON met.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
LEFT JOIN molecule_dictionary parent ON met.metabolite_record_id = parent.molregno
JOIN target_dictionary td ON met.enzyme_tid = td.tid
WHERE td.target_type = 'CYPI' AND td.pref_name IN ('CYP3A4', 'CYP3A5')
LIMIT 200
