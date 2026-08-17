SELECT cs.canonical_smiles, cr.compound_name, m.met_conversion, m.pathway_key
FROM metabolism m
JOIN compound_records cr ON cr.record_id = m.substrate_record_id
JOIN compound_structures cs ON cs.molregno = cr.molregno
LIMIT 200;
