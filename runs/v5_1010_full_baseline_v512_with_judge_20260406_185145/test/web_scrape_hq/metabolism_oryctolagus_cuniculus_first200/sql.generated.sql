SELECT
  cs.canonical_smiles,
  sub_mol.pref_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  met.met_conversion,
  met.pathway_key,
  met.organism,
  met.enzyme_name
FROM metabolism met
JOIN compound_records sub_cr ON met.substrate_record_id = sub_cr.record_id
JOIN molecule_dictionary sub_mol ON sub_cr.molregno = sub_mol.molregno
JOIN compound_structures cs ON sub_mol.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON sub_mol.molregno = mh.molregno
LEFT JOIN molecule_dictionary parent_mol ON mh.parent_molregno = parent_mol.molregno
WHERE met.organism = 'Oryctolagus cuniculus'
LIMIT 200
