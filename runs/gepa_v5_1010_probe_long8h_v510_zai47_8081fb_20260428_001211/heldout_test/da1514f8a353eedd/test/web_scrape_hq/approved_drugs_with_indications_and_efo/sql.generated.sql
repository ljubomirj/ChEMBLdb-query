SELECT DISTINCT
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  di.efo_id AS indication_curie,
  di.efo_term AS indication_label,
  di.max_phase_for_ind
FROM molecule_dictionary md
INNER JOIN compound_structures cs ON md.molregno = cs.molregno
INNER JOIN drug_indication di ON md.molregno = di.molregno
WHERE md.max_phase = 4
  AND di.efo_id IS NOT NULL
  AND di.efo_term IS NOT NULL
ORDER BY
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  indication_curie,
  indication_label,
  di.max_phase_for_ind
