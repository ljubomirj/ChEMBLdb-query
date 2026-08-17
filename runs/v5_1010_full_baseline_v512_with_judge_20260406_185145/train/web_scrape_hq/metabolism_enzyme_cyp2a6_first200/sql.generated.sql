SELECT DISTINCT
  m.molregno AS molregno,
  m.pref_name AS substrate_compound_name,
  parent.molregno AS parent_molregno,
  parent.pref_name AS parent_compound_name,
  m.met_conversion AS met_conversion,
  m.pathway_key AS pathway_key,
  m.organism AS organism,
  m.enzyme_name AS enzyme_name,
  cs.canonical_smiles AS canonical_smiles
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN molecule_dictionary m ON cr.molregno = m.molregno
LEFT JOIN molecule_hierarchy mh ON m.molregno = mh.molregno
LEFT JOIN molecule_dictionary parent ON mh.parent_molregno = parent.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE m.enzyme_name = 'CYP2A6'
  AND m.met_conversion IS NOT NULL
  AND m.met_conversion <> ''
LIMIT 200
