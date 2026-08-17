SELECT cs.canonical_smiles,
       m.pref_name AS compound_name,
       met.met_conversion,
       met.pathway_key
FROM metabolism met
JOIN compound_records cr ON cr.record_id = met.substrate_record_id
JOIN molecule_dictionary m ON m.molregno = cr.molregno
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE met.met_conversion IS NOT NULL
LIMIT 200
