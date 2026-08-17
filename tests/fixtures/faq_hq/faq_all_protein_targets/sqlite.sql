SELECT t.chembl_id AS target_chembl_id,
t.pref_name AS target_name,
t.target_type,
c.accession AS protein_accession,
c.sequence AS protein_sequence
FROM target_dictionary t
JOIN target_type tt ON t.target_type = tt.target_type
JOIN target_components tc ON t.tid = tc.tid
JOIN component_sequences c ON tc.component_id = c.component_id
WHERE tt.parent_type = 'PROTEIN';
