SELECT DISTINCT
  cs.canonical_smiles,
  sub.molregno AS substrate_compound_name,
  parent.molregno AS parent_compound_name,
  met.met_conversion,
  met.pathway_key,
  td.organism,
  met.enzyme_name
FROM metabolism met
JOIN compound_records cr ON met.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
LEFT JOIN molecule_hierarchy mh ON sub.molregno = mh.molregno AND mh.parent_molregno IS NOT NULL
LEFT JOIN molecule_dictionary parent ON mh.parent_molregno = parent.molregno
JOIN target_dictionary td ON met.tid = td.tid
WHERE td.organism = 'Callithrix jacchus'
LIMIT 200
