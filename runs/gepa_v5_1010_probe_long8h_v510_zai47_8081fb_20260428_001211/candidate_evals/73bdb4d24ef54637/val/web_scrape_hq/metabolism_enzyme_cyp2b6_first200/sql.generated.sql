SELECT
  substr_struct.canonical_smiles,
  substr_rec.compound_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  met.met_conversion,
  met.pathway_key,
  met.organism,
  met.enzyme_name
FROM metabolism met
INNER JOIN compound_records substr_rec ON met.substrate_record_id = substr_rec.record_id
INNER JOIN compound_structures substr_struct ON substr_rec.molregno = substr_struct.molregno
INNER JOIN molecule_dictionary parent_mol ON met.drug_record_id = parent_mol.molregno
WHERE met.enzyme_name = 'CYP2B6'
ORDER BY
  substr_struct.canonical_smiles,
  substr_rec.compound_name,
  parent_mol.pref_name,
  met.met_conversion,
  met.pathway_key,
  met.organism,
  met.enzyme_name
LIMIT 200
