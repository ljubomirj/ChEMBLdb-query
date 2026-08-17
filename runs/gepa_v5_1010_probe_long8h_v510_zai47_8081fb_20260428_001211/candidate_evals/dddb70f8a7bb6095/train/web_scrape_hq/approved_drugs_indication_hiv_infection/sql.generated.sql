SELECT
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  'EFO:' || di.efo_id AS indication_curie,
  di.mesh_heading AS indication_label,
  di.max_phase_for_ind
FROM molecule_dictionary md
JOIN drug_indication di ON di.molregno = md.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE di.max_phase_for_ind = 4
  AND (di.mesh_heading LIKE '%HIV%' OR di.efo_term LIKE '%HIV%')
ORDER BY
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  indication_curie,
  indication_label,
  di.max_phase_for_ind
