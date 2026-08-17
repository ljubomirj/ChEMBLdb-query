SELECT DISTINCT
  cs.canonical_smiles,
  sub.molregno AS substrate_compound_name,
  parent.molregno AS parent_compound_name,
  met.met_conversion,
  met.pathway_key,
  met.organism,
  enz.enzyme_name
FROM metabolism met
JOIN compound_records sub_rec ON met.substrate_record_id = sub_rec.record_id
JOIN molecule_dictionary sub ON sub_rec.molregno = sub.molregno
LEFT JOIN molecule_hierarchy mh ON sub.molregno = mh.molregno
LEFT JOIN molecule_dictionary parent ON mh.parent_molregno = parent.molregno
JOIN compound_structures sub_cs ON sub.molregno = sub_cs.molregno
JOIN target_dictionary enz ON met.enzyme_tid = enz.tid
WHERE enz.pref_name = 'P450 reductase'
LIMIT 200;
