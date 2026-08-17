SELECT DISTINCT
  m.chembl_id,
  m.pref_name,
  cs.canonical_smiles,
  di.efo_id AS indication_curie,
  di.efo_term AS indication_label,
  di.max_phase_for_ind
FROM molecule_dictionary m
JOIN drug_indication di ON di.molregno = m.molregno
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
WHERE m.max_phase = 4
  AND di.efo_id IS NOT NULL
  AND di.efo_term IS NOT NULL
ORDER BY
  m.chembl_id ASC,
  m.pref_name ASC,
  cs.canonical_smiles ASC,
  di.efo_id ASC,
  di.efo_term ASC,
  di.max_phase_for_ind ASC
