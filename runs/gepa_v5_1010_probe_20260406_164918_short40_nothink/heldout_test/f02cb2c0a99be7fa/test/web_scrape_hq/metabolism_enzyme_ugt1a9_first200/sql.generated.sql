SELECT DISTINCT cs.canonical_smiles AS canonical_smiles,
       m.pref_name AS substrate_compound_name,
       parent_mol.pref_name AS parent_compound_name,
       met.met_conversion,
       met.pathway_key,
       t.organism,
       t.pref_name AS enzyme_name
FROM metabolism met
JOIN compound_records subcr ON met.substrate_record_id = subcr.record_id
JOIN molecule_dictionary m ON subcr.molregno = m.molregno
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON mh.molregno = m.molregno
LEFT JOIN molecule_dictionary parent_mol ON mh.parent_molregno = parent_mol.molregno
JOIN target_dictionary t ON met.enzyme_tid = t.tid
WHERE t.pref_name = 'UGT1A9'
LIMIT 200;
