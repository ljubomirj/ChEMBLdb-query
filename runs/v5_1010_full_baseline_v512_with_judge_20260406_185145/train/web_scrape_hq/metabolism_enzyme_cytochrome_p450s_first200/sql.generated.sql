SELECT DISTINCT
  m.canonical_smiles AS canonical_smiles,
  s1.pref_name AS substrate_compound_name,
  s2.pref_name AS parent_compound_name,
  met.met_conversion,
  met.pathway_key,
  t.organism,
  e.enzyme_name
FROM metabolism met
JOIN compound_records cr_substrate ON met.substrate_record_id = cr_substrate.record_id
JOIN molecule_dictionary s1 ON cr_substrate.molregno = s1.molregno
JOIN molecule_hierarchy mh ON s1.molregno = mh.molregno
JOIN molecule_dictionary s2 ON mh.parent_molregno = s2.molregno
JOIN compound_records cr_parent ON s2.molregno = cr_parent.molregno
JOIN molecule_dictionary m ON cr_parent.molregno = m.molregno
LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
JOIN target_dictionary t ON met.tid = t.tid
JOIN target_components tc ON t.tid = tc.tid
JOIN protein_classification pc ON tc.component_id = pc.protein_class_id
WHERE t.organism = 'Homo sapiens'
  AND pc.pref_name LIKE '%Cytochrome P450%'
LIMIT 200;
