SELECT cs.canonical_smiles,
       sub.pref_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       m.met_conversion,
       m.pathway_key,
       m.organism,
       t.pref_name AS enzyme_name
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
LEFT JOIN compound_structures cs ON sub.molregno = cs.molregno
JOIN molecule_dictionary parent ON m.met_id = parent.molregno
JOIN target_dictionary t ON m.enzyme_tid = t.tid
WHERE t.pref_name = 'CYP3A5'
LIMIT 200;
