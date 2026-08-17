SELECT DISTINCT 
  cs.canonical_smiles,
  sub.molregno AS substrate_compound_molregno,
  parent.molregno AS parent_compound_molregno,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records sub_rec ON m.substrate_record_id = sub_rec.record_id
JOIN molecule_dictionary sub ON sub_rec.molregno = sub.molregno
JOIN molecule_dictionary parent ON sub.parent_molregno = parent.molregno
LEFT JOIN compound_structures cs ON sub.molregno = cs.molregno
WHERE m.enzyme_name = 'CYP2C19'
LIMIT 200;
