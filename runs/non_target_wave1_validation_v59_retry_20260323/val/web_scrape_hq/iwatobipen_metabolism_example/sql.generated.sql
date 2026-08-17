SELECT
  cs.canonical_smiles,
  cr.compound_name,
  m.met_conversion,
  m.pathway_key
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
LIMIT 200
