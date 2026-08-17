SELECT DISTINCT cs.canonical_smiles AS canonical_smiles,
       sub.pref_name AS substrate_compound_name,
       parent.pref_name AS parent_compound_name,
       met.met_conversion AS met_conversion,
       met.pathway_key AS pathway_key,
       met.organism AS organism,
       t.pref_name AS enzyme_name
FROM metabolism met
JOIN compound_records sub_rec ON met.substrate_record_id = sub_rec.record_id
JOIN molecule_dictionary sub ON sub.molregno = sub_rec.molregno
JOIN compound_structures cs ON cs.molregno = sub_rec.molregno
JOIN molecule_dictionary parent ON parent.molregno = met.metabolite_record_id
JOIN target_dictionary t ON t.tid = met.enzyme_tid
WHERE t.pref_name = 'CYP2E1'
LIMIT 200
