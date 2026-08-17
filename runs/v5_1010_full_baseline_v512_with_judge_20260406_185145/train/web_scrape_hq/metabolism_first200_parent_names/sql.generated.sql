SELECT cs.canonical_smiles AS canonical_smiles,
       cr.compound_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       m.met_conversion AS met_conversion,
       m.pathway_key AS pathway_key
FROM metabolism m
JOIN compound_records cr ON cr.record_id = m.substrate_record_id
JOIN molecule_dictionary substrate ON substrate.molregno = cr.molregno
LEFT JOIN molecule_hierarchy mh ON mh.molregno = substrate.molregno AND mh.parent_molregno = substrate.molregno
LEFT JOIN molecule_dictionary parent ON parent.molregno = mh.parent_molregno
JOIN compound_structures cs ON cs.molregno = substrate.molregno
WHERE m.pathway_key IS NOT NULL
LIMIT 200
