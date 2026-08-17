SELECT cs.canonical_smiles,
       cr.compound_name AS substrate_compound_name,
       md.pref_name AS parent_compound_name,
       m.met_conversion,
       m.pathway_key,
       m.organism,
       m.enzyme_name
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON cr.molregno = mh.molregno
LEFT JOIN molecule_dictionary md ON mh.parent_molregno = md.molregno
WHERE m.enzyme_name = 'CYP2C9'
  AND cs.canonical_smiles IS NOT NULL
LIMIT 200
