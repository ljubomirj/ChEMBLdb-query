SELECT cs.canonical_smiles AS canonical_smiles,
       s.pref_name AS substrate_compound_name,
       p.pref_name AS parent_compound_name,
       m.met_conversion AS met_conversion,
       m.pathway_key AS pathway_key,
       m.organism AS organism,
       e.pref_name AS enzyme_name
FROM metabolism m
JOIN compound_structures cs ON cs.molregno = m.substrate_record_id
JOIN molecule_dictionary s ON s.molregno = m.substrate_record_id
LEFT JOIN molecule_dictionary p ON p.molregno = m.met_id
JOIN target_dictionary e ON e.tid = m.enzyme_tid
WHERE e.pref_name = 'CYP2B6'
LIMIT 200
