SELECT
  substr_struct.canonical_smiles,
  substr_cr.compound_name AS substrate_compound_name,
  parent_cr.compound_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records substr_cr ON m.substrate_record_id = substr_cr.record_id
JOIN molecule_dictionary substr_md ON substr_cr.molregno = substr_md.molregno
JOIN compound_structures substr_struct ON substr_md.molregno = substr_struct.molregno
LEFT JOIN compound_records parent_cr ON m.drug_record_id = parent_cr.record_id
WHERE m.enzyme_name = 'CYP2B6'
ORDER BY
  substr_struct.canonical_smiles,
  substr_cr.compound_name,
  parent_cr.compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
LIMIT 200
