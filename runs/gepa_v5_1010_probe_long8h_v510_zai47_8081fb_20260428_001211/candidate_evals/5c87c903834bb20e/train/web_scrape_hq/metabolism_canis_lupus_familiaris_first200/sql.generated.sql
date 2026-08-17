SELECT
  sub_struct.canonical_smiles,
  sub_rec.compound_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records sub_rec ON m.substrate_record_id = sub_rec.record_id
JOIN compound_structures sub_struct ON sub_rec.molregno = sub_struct.molregno
JOIN compound_records parent_rec ON m.drug_record_id = parent_rec.record_id
JOIN molecule_dictionary parent_mol ON parent_rec.molregno = parent_mol.molregno
WHERE m.organism = 'Canis lupus familiaris'
ORDER BY
  sub_struct.canonical_smiles ASC,
  sub_rec.compound_name ASC,
  parent_mol.pref_name ASC,
  m.met_conversion ASC,
  m.pathway_key ASC,
  m.organism ASC,
  m.enzyme_name ASC
LIMIT 200;
