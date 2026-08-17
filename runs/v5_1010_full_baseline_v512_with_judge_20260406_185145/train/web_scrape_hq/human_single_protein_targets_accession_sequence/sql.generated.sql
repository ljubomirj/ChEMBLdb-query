SELECT td.chembl_id AS target_chembl_id,
       td.pref_name AS target_name,
       td.target_type,
       td.chembl_id AS protein_accession,
       cs.sequence AS protein_sequence
FROM target_dictionary td
LEFT JOIN component_sequences cs ON cs.tax_id = td.tax_id
WHERE td.target_type = 'SINGLE PROTEIN'
  AND td.organism = 'Homo sapiens'
ORDER BY td.chembl_id, td.pref_name, td.target_type, cs.sequence
