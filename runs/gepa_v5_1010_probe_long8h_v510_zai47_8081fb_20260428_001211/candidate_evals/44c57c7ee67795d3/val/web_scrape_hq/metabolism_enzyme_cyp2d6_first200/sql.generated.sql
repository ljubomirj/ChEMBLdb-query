SELECT
  cs.canonical_smiles,
  cr_sub.compound_name AS substrate_compound_name,
  cr_par.compound_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records cr_sub ON m.substrate_record_id = cr_sub.record_id
JOIN molecule_dictionary md_sub ON cr_sub.molregno = md_sub.molregno
JOIN compound_structures cs ON md_sub.molregno = cs.molregno
JOIN compound_records cr_par ON m.drug_record_id = cr_par.record_id
WHERE m.enzyme_name = 'CYP2D6'
ORDER BY
  cs.canonical_smiles ASC,
  substrate_compound_name ASC,
  parent_compound_name ASC,
  m.met_conversion ASC,
  m.pathway_key ASC,
  m.organism ASC,
  m.enzyme_name ASC
LIMIT 200;
