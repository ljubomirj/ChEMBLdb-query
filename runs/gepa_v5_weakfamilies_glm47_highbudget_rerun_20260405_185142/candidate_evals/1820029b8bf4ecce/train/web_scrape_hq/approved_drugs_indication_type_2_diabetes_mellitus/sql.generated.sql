SELECT
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  ir.ref_id AS indication_curie,
  ir.ref_id AS indication_label,
  di.max_phase_for_ind AS max_phase_for_ind
FROM molecule_dictionary md
JOIN drug_indication di ON md.molregno = di.molregno
JOIN indication_refs ir ON di.drugind_id = ir.drugind_id
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE di.max_phase_for_ind = 4
  AND ir.ref_id LIKE '%type 2 diabetes mellitus%'
ORDER BY
  md.chembl_id,
  md.pref_name,
  cs.canonical_smiles,
  ir.ref_id,
  di.max_phase_for_ind
