SELECT
    chembl_id,
    pref_name
FROM MOLECULE_DICTIONARY
WHERE
    chebi_par_id IS NULL
    AND pref_name IS NOT NULL
