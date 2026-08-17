SELECT
  cs.canonical_smiles,
  sub_mol.pref_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records cr_sub ON m.substrate_record_id = cr_sub.record_id
JOIN molecule_dictionary sub_mol ON cr_sub.molregno = sub_mol.molregno
JOIN compound_structures cs ON sub_mol.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON sub_mol.molregno = mh.molregno
LEFT JOIN molecule_dictionary parent_mol ON mh.parent_molregno = parent_mol.molregno
WHERE m.enzyme_name = 'UGT1A9'
ORDER BY
  cs.canonical_smiles,
  sub_mol.pref_name,
  parent_mol.pref_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
LIMIT 200
