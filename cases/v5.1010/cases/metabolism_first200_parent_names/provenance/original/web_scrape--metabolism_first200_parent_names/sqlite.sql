SELECT cs.canonical_smiles,
       cr.compound_name AS substrate_compound_name,
       parent_md.pref_name AS parent_compound_name,
       m.met_conversion,
       m.pathway_key
FROM metabolism m
JOIN compound_records cr ON cr.record_id = m.substrate_record_id
JOIN compound_structures cs ON cs.molregno = cr.molregno
LEFT JOIN molecule_hierarchy mh ON mh.molregno = cr.molregno
LEFT JOIN molecule_dictionary parent_md ON parent_md.molregno = mh.parent_molregno
LIMIT 200;
