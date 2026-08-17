SELECT
  cs.canonical_smiles,
  m_sub.pref_name AS substrate_compound_name,
  m_par.pref_name AS parent_compound_name,
  met.met_conversion,
  met.pathway_key,
  met.organism,
  met.enzyme_name
FROM metabolism met
JOIN compound_records cr_sub ON met.substrate_record_id = cr_sub.record_id
JOIN molecule_dictionary m_sub ON cr_sub.molregno = m_sub.molregno
JOIN compound_structures cs ON m_sub.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON m_sub.molregno = mh.molregno
LEFT JOIN molecule_dictionary m_par ON mh.parent_molregno = m_par.molregno
WHERE met.enzyme_name = 'UGT1A9'
LIMIT 200
