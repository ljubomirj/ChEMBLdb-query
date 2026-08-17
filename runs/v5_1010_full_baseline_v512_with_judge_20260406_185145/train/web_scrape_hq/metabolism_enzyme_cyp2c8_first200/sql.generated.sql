SELECT DISTINCT cs.canonical_smiles AS canonical_smiles,
       sub.pref_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       m.met_conversion AS met_conversion,
       m.pathway_key AS pathway_key,
       m.organism AS organism,
       m.enzyme_name AS enzyme_name
FROM metabolism m
LEFT JOIN compound_records cr ON m.substrate_record_id = cr.record_id
LEFT JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
LEFT JOIN molecule_dictionary parent ON m.metabolism.substrate_record_id = parent.molregno
LEFT JOIN compound_structures cs ON sub.molregno = cs.molregno
LEFT JOIN target_dictionary td ON m.tid = td.tid
WHERE td.target_type = 'PROTEIN'
  AND td.pref_name = 'CYP2C8'
LIMIT 200
