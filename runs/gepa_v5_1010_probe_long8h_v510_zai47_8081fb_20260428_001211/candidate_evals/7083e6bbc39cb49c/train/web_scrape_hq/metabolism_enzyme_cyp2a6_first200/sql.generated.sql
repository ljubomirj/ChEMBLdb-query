SELECT
  cs.canonical_smiles,
  sub_rec.compound_name AS substrate_compound_name,
  par_rec.compound_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
INNER JOIN compound_records sub_rec ON m.substrate_record_id = sub_rec.record_id
INNER JOIN compound_records par_rec ON m.drug_record_id = par_rec.record_id
INNER JOIN compound_structures cs ON sub_rec.molregno = cs.molregno
WHERE m.enzyme_name = 'CYP2A6'
ORDER BY cs.canonical_smiles, sub_rec.compound_name, par_rec.compound_name, m.met_conversion, m.pathway_key, m.organism, m.enzyme_name
LIMIT 200
