SELECT DISTINCT cs.canonical_smiles AS canonical_smiles,
       sub.molregno AS substrate_compound_name,
       parent.molregno AS parent_compound_name,
       met.met_conversion AS met_conversion,
       met.pathway_key AS pathway_key,
       met.organism AS organism,
       met.enzyme_name AS enzyme_name
FROM metabolism met
LEFT JOIN compound_records cr ON met.substrate_record_id = cr.record_id
LEFT JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
LEFT JOIN molecule_dictionary parent ON met.met_id = parent.molregno
LEFT JOIN compound_structures cs ON sub.molregno = cs.molregno
WHERE met.organism = 'Rattus norvegicus'
LIMIT 200
