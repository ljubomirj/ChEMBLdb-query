SELECT
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  di.efo_id AS indication_curie,
  di.mesh_heading AS indication_label,
  di.max_phase_for_ind
FROM molecule_dictionary md
JOIN drug_indication di ON md.molregno = di.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE md.max_phase = 4
  AND di.mesh_heading = 'Cardiovascular Diseases'
ORDER BY md.chembl_id
