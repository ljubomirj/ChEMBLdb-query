SELECT
  cs.canonical_smiles,
  cr_sub.compound_name AS substrate_compound_name,
  md_parent.pref_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records cr_sub ON m.substrate_record_id = cr_sub.record_id
JOIN compound_structures cs ON cr_sub.molregno = cs.molregno
JOIN compound_records cr_parent ON m.drug_record_id = cr_parent.record_id
JOIN molecule_dictionary md_parent ON cr_parent.molregno = md_parent.molregno
WHERE m.enzyme_name = 'CYP2B6'
ORDER BY cs.canonical_smiles ASC, cr_sub.compound_name ASC, md_parent.pref_name ASC, m.met_conversion ASC, m.pathway_key ASC, m.organism ASC, m.enzyme_name ASC
LIMIT 200
