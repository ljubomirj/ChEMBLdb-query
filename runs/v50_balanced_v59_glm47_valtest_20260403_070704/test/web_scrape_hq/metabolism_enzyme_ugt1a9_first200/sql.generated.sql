SELECT
  cs.canonical_smiles,
  cr.compound_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON cr.molregno = mh.molregno
LEFT JOIN molecule_dictionary parent_mol ON mh.parent_molregno = parent_mol.molregno
WHERE m.enzyme_name = 'UGT1A9'
LIMIT 200
