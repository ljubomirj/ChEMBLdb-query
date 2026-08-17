SELECT DISTINCT cs.canonical_smiles AS canonical_smiles,
       sub.pref_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       m.met_conversion AS met_conversion,
       m.pathway_key AS pathway_key,
       m.organism AS organism,
       t.pref_name AS enzyme_name
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
JOIN molecule_dictionary parent ON m.substrate_record_id = parent.molregno
JOIN compound_structures cs ON sub.molregno = cs.molregno
JOIN target_dictionary t ON m.enzyme_tid = t.tid
WHERE t.target_type = 'PROTEIN' AND t.pref_name LIKE '%P450%'
LIMIT 200
