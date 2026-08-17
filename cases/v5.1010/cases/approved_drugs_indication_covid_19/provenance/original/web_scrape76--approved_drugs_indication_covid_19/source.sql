SELECT DISTINCT
  md.chembl_id AS chembl_id,
  md.pref_name AS pref_name,
  cs.canonical_smiles AS canonical_smiles,
  di.efo_id AS indication_curie,
  di.efo_term AS indication_label,
  di.max_phase_for_ind AS max_phase_for_ind
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN drug_indication di ON md.molregno = di.molregno
WHERE md.max_phase = 4
  AND di.efo_term = 'COVID-19'
  AND di.efo_id IS NOT NULL
