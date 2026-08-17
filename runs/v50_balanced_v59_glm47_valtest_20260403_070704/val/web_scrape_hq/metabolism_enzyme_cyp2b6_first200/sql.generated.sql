SELECT
  cs.canonical_smiles,
  md_sub.pref_name AS substrate_compound_name,
  md_parent.pref_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
INNER JOIN compound_records cr_sub ON m.substrate_record_id = cr_sub.record_id
INNER JOIN compound_structures cs ON cr_sub.molregno = cs.molregno
INNER JOIN molecule_dictionary md_sub ON cr_sub.molregno = md_sub.molregno
LEFT JOIN molecule_hierarchy mh ON md_sub.molregno = mh.molregno
LEFT JOIN molecule_dictionary md_parent ON mh.parent_molregno = md_parent.molregno
WHERE m.enzyme_name = 'CYP2B6'
LIMIT 200
