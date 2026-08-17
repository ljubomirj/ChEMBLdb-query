SELECT DISTINCT
  cs.canonical_smiles AS canonical_smiles,
  sub_mol.pref_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  met.met_conversion AS met_conversion,
  met.pathway_key AS pathway_key,
  met.organism AS organism,
  met.enzyme_name AS enzyme_name
FROM metabolism met
INNER JOIN compound_records substrate_rec ON met.substrate_record_id = substrate_rec.record_id
INNER JOIN molecule_dictionary sub_mol ON sub_mol.molregno = substrate_rec.molregno
INNER JOIN compound_structures cs ON cs.molregno = sub_mol.molregno
INNER JOIN molecule_dictionary parent_mol ON parent_mol.molregno = met.metabolite_record_id
WHERE met.enzyme_name IN ('CYP3A4', 'CYP3A5')
LIMIT 200
