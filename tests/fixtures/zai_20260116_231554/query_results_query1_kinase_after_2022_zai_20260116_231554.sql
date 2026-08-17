SELECT
    compound_structures.canonical_smiles,
    molecule_dictionary.chembl_id,
    target_dictionary.pref_name AS target_name,
    docs.year,
    docs.doi,
    activities.standard_value AS IC50
FROM
    molecule_dictionary
JOIN
    compound_structures ON molecule_dictionary.molregno = compound_structures.molregno
JOIN
    activities ON molecule_dictionary.molregno = activities.molregno
JOIN
    assays ON activities.assay_id = assays.assay_id
JOIN
    target_dictionary ON assays.tid = target_dictionary.tid
JOIN
    docs ON assays.doc_id = docs.doc_id
WHERE
    docs.year > 2022
    AND activities.standard_type = 'IC50'
    AND target_dictionary.pref_name LIKE '%kinase%'
