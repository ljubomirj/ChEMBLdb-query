SELECT
  sub_struct.canonical_smiles,
  sub_mol.pref_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
FROM metabolism m
JOIN compound_records sub_rec ON m.substrate_record_id = sub_rec.record_id
JOIN molecule_dictionary sub_mol ON sub_rec.molregno = sub_mol.molregno
JOIN compound_structures sub_struct ON sub_mol.molregno = sub_struct.molregno
JOIN molecule_hierarchy mh ON sub_mol.molregno = mh.molregno
JOIN molecule_dictionary parent_mol ON mh.parent_molregno = parent_mol.molregno
JOIN compound_records parent_rec ON parent_mol.molregno = parent_rec.molregno
JOIN docs d ON parent_rec.doc_id = d.doc_id
WHERE m.organism = 'Canis lupus familiaris'
ORDER BY
  sub_struct.canonical_smiles,
  sub_mol.pref_name,
  parent_mol.pref_name,
  m.met_conversion,
  m.pathway_key,
  m.organism,
  m.enzyme_name
LIMIT 200
