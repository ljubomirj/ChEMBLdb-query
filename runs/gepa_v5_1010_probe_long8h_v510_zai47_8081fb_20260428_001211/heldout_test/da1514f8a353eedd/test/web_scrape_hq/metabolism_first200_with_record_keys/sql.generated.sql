SELECT
  cs.canonical_smiles,
  m.substrate_record_id,
  m.metabolite_record_id,
  substrate_records.compound_key AS substrate_compound_key,
  metabolite_records.compound_key AS metabolite_compound_key,
  m.met_conversion,
  m.pathway_key
FROM metabolism m
INNER JOIN compound_records AS substrate_records
  ON m.substrate_record_id = substrate_records.record_id
INNER JOIN compound_structures AS cs
  ON substrate_records.molregno = cs.molregno
LEFT JOIN compound_records AS metabolite_records
  ON m.metabolite_record_id = metabolite_records.record_id
ORDER BY
  cs.canonical_smiles,
  m.substrate_record_id,
  m.metabolite_record_id,
  substrate_records.compound_key,
  metabolite_records.compound_key,
  m.met_conversion,
  m.pathway_key
LIMIT 200;
