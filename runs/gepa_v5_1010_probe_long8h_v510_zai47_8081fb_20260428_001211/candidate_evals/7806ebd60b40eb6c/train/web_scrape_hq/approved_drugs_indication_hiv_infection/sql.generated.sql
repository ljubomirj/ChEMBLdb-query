SELECT
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  di.efo_id AS indication_curie,
  di.mesh_heading AS indication_label,
  di.max_phase_for_ind
FROM molecule_dictionary md
INNER JOIN drug_indication di
  ON md.molregno = di.molregno
INNER JOIN compound_structures cs
  ON md.molregno = cs.molregno
WHERE md.max_phase >= 4
  AND di.mesh_heading = 'HIV Infection'
ORDER BY
  md.chembl_id ASC,
  md.pref_name ASC,
  cs.canonical_smiles ASC,
  di.efo_id ASC,
  di.mesh_heading ASC,
  di.max_phase_for_ind ASC
