SELECT
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.target_type AS target_type,
  cs.accession AS protein_accession,
  cs.sequence AS protein_sequence
FROM target_dictionary td
JOIN target_components tc ON tc.tid = td.tid
JOIN component_sequences cs ON cs.component_id = tc.component_id
WHERE td.target_type = 'SINGLE PROTEIN'
ORDER BY target_chembl_id, target_name, target_type, protein_accession, protein_sequence
