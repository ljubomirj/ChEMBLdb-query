SELECT
    MOLECULE_DICTIONARY.chembl_id,
    MOLECULE_DICTIONARY.pref_name,
    MOLECULE_DICTIONARY.chebi_par_id,
    DRUG_INDICATION.mesh_id,
    DRUG_INDICATION.mesh_heading,
    DRUG_INDICATION.efo_id AS indication_curie,
    DRUG_INDICATION.efo_term AS indication_label,
    DRUG_INDICATION.max_phase_for_ind
FROM MOLECULE_DICTIONARY
JOIN DRUG_INDICATION ON MOLECULE_DICTIONARY.molregno == DRUG_INDICATION.molregno
