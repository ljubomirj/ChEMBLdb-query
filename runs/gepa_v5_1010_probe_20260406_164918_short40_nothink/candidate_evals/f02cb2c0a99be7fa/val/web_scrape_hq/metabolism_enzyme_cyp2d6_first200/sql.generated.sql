SELECT DISTINCT substrate.pref_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       met.met_conversion,
       met.pathway_key,
       met.organism,
       met.enzyme_name,
       cs.canonical_smiles
FROM metabolism met
JOIN compound_records cr ON met.substrate_record_id = cr.record_id
JOIN molecule_dictionary substrate ON cr.molregno = substrate.molregno
LEFT JOIN molecule_dictionary parent ON met.metabolism.substrate_record_id = parent.molregno
LEFT JOIN compound_structures cs ON substrate.molregno = cs.molregno
JOIN target_dictionary td ON substrate.tid = td.tid
WHERE td.pref_name = 'CYP2D6'
  AND met.met_conversion IS NOT NULL
  AND met.met_conversion != ''
LIMIT 200;
