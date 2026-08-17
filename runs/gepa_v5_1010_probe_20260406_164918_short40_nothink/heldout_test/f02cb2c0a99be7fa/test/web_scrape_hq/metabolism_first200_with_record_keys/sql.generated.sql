SELECT cs.canonical_smiles,
       mr.record_id AS substrate_record_id,
       m.metabolite_record_id,
       mr2.compound_key AS substrate_compound_key,
       mr2.src_compound_id AS metabolite_compound_key,
       m.met_conversion,
       m.pathway_key
FROM metabolism m
JOIN compound_records mr ON m.substrate_record_id = mr.record_id
JOIN compound_structures cs ON mr.molregno = cs.molregno
JOIN compound_records mr2 ON m.metabolite_record_id = mr2.record_id
LEFT JOIN compound_structures cs2 ON mr2.molregno = cs2.molregno
WHERE cs.canonical_smiles IS NOT NULL
  AND m.met_conversion IS NOT NULL
  AND m.pathway_key IS NOT NULL
LIMIT 200
