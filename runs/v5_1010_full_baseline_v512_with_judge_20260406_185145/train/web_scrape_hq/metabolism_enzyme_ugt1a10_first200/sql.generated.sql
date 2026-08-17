SELECT cs.canonical_smiles AS canonical_smiles,
       sub.pref_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       met.met_conversion AS met_conversion,
       met.pathway_key AS pathway_key,
       sub.organism AS organism,
       t.pref_name AS enzyme_name
FROM metabolism met
JOIN compound_records substrate_records ON met.substrate_record_id = substrate_records.record_id
JOIN molecule_dictionary sub ON substrate_records.molregno = sub.molregno
LEFT JOIN compound_structures cs ON sub.molregno = cs.molregno
JOIN molecule_dictionary parent ON met.drug_record_id = parent.molregno
LEFT JOIN compound_structures parent_structures ON parent.molregno = parent_structures.molregno
JOIN target_dictionary t ON met.tid = t.tid
WHERE t.pref_name = 'UGT1A10'
LIMIT 200
