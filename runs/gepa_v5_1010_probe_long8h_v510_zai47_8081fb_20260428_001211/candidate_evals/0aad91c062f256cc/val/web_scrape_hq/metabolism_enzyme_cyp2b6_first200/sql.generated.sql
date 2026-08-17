SELECT
  compound_structures.canonical_smiles,
  substrate_records.compound_name AS substrate_compound_name,
  parent_records.compound_name AS parent_compound_name,
  metabolism.met_conversion,
  metabolism.pathway_key,
  metabolism.organism,
  metabolism.enzyme_name
FROM metabolism
JOIN compound_records AS substrate_records
  ON metabolism.substrate_record_id = substrate_records.record_id
JOIN molecule_dictionary
  ON substrate_records.molregno = molecule_dictionary.molregno
JOIN compound_structures
  ON molecule_dictionary.molregno = compound_structures.molregno
LEFT JOIN compound_records AS parent_records
  ON metabolism.drug_record_id = parent_records.record_id
WHERE metabolism.enzyme_name = 'CYP2B6'
ORDER BY
  compound_structures.canonical_smiles ASC,
  substrate_compound_name ASC,
  parent_compound_name ASC,
  metabolism.met_conversion ASC,
  metabolism.pathway_key ASC,
  metabolism.organism ASC,
  metabolism.enzyme_name ASC
LIMIT 200;
