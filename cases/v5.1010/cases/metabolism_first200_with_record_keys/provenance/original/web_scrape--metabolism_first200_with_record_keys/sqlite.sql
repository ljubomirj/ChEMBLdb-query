SELECT cs.canonical_smiles,
       m.substrate_record_id,
       m.metabolite_record_id,
       substrate_cr.compound_key AS substrate_compound_key,
       metabolite_cr.compound_key AS metabolite_compound_key,
       m.met_conversion,
       m.pathway_key
FROM metabolism m
JOIN compound_records substrate_cr ON substrate_cr.record_id = m.substrate_record_id
JOIN compound_structures cs ON cs.molregno = substrate_cr.molregno
LEFT JOIN compound_records metabolite_cr ON metabolite_cr.record_id = m.metabolite_record_id
LIMIT 200;
