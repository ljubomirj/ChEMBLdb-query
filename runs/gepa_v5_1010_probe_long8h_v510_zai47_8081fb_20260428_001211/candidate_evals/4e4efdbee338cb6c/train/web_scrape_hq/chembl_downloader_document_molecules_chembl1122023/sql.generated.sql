SELECT molecule_dictionary.chembl_id AS molecule_chembl_id,
       molecule_dictionary.pref_name AS molecule_name,
       molecule_dictionary.max_phase AS max_phase,
       molecule_dictionary.molecule_type AS molecule_type,
       compound_structures.canonical_smiles AS canonical_smiles
FROM molecule_dictionary
LEFT JOIN compound_structures ON molecule_dictionary.molregno = compound_structures.molregno
WHERE molecule_dictionary.chembl_id = 'CHEMBL1122023'
ORDER BY molecule_chembl_id;

</think>
