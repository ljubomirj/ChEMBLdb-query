SELECT cs.canonical_smiles,
       sub.pref_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       met.met_conversion,
       met.pathway_key,
       met.organism,
       tgt.pref_name AS enzyme_name
FROM metabolism met
JOIN compound_records cr ON met.substrate_record_id = cr.record_id
JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
LEFT JOIN compound_structures cs ON sub.molregno = cs.molregno
JOIN molecule_dictionary parent ON met.met_id = parent.molregno
JOIN target_dictionary tgt ON met.enzyme_tid = tgt.tid
WHERE tgt.pref_name = 'CYP2B6'
LIMIT 200
