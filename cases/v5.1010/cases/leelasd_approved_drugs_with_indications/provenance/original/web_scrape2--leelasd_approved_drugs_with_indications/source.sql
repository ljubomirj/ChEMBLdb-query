SELECT DISTINCT md.chembl_id, md.pref_name, cs.canonical_smiles, md.max_phase, di.mesh_heading, md.first_approval
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN drug_indication di ON md.molregno = di.molregno
WHERE md.max_phase = 4
ORDER BY md.first_approval DESC;
