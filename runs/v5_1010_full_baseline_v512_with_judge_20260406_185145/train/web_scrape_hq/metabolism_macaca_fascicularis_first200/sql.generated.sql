SELECT
  act.met_conversion,
  act.pathway_key,
  act.enzyme_name,
  a.assay_organism,
  md.pref_name AS substrate_compound_name,
  parent_mol.pref_name AS parent_compound_name,
  cs.canonical_smiles
FROM metabolism met
LEFT JOIN activities act ON met.met_id = act.activity_id
LEFT JOIN assays a ON act.assay_id = a.assay_id
LEFT JOIN compound_records cr ON act.record_id = cr.record_id
LEFT JOIN molecule_dictionary md ON cr.molregno = md.molregno
LEFT JOIN molecule_hierarchy mh ON md.molregno = mh.molregno
LEFT JOIN molecule_dictionary parent_mol ON mh.parent_molregno = parent_mol.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE a.assay_organism = 'Macaca fascicularis'
LIMIT 200
