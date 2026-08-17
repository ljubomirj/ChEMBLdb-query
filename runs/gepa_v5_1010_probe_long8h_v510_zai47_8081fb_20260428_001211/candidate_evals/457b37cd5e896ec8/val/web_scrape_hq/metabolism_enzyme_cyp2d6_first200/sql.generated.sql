SELECT
  cs.canonical_smiles,
  cr_sub.compound_name AS substrate_compound_name,
  md_parent.pref_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
INNER JOIN compound_records cr_sub
  ON m.substrate_record_id = cr_sub.record_id
LEFT JOIN molecule_dictionary md_parent
  ON cr_sub.molregno = md_parent.molregno
LEFT JOIN compound_structures cs
  ON cr_sub.molregno = cs.molregno
WHERE m.enzyme_name = 'CYP2D6'
ORDER BY
  cs.canonical_smiles ASC,
  cr_sub.compound_name ASC,
  md_parent.pref_name ASC,
  m.met_conversion ASC,
  m.pathway_key ASC,
  m.organism ASC,
  m.enzyme_name ASC
LIMIT 200
