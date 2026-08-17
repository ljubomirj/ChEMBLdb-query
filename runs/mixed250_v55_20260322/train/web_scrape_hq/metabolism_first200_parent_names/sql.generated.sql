SELECT
  cs.canonical_smiles,
  cr_sub.compound_name AS substrate_compound_name,
  m_parent.pref_name AS parent_compound_name,
  met.met_conversion,
  met.pathway_key
FROM metabolism met
JOIN compound_records cr_sub ON met.substrate_record_id = cr_sub.record_id
JOIN compound_structures cs ON cr_sub.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON cr_sub.molregno = mh.molregno
LEFT JOIN molecule_dictionary m_parent ON mh.parent_molregno = m_parent.molregno
LIMIT 200
