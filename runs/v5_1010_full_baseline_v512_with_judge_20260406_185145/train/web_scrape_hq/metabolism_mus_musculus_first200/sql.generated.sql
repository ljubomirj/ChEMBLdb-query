SELECT DISTINCT
  m.molregno AS substrate_molregno,
  m.pref_name AS substrate_compound_name,
  s.standard_value AS met_conversion,
  s.standard_units AS pathway_key,
  t.organism AS organism,
  e.enzyme_name AS enzyme_name,
  cs.canonical_smiles AS canonical_smiles,
  parent.pref_name AS parent_compound_name
FROM metabolism m
JOIN compound_records r ON m.substrate_record_id = r.record_id
JOIN molecule_dictionary m ON r.molregno = m.molregno
JOIN activity_properties s ON m.activity_id = s.activity_id
JOIN assays a ON m.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
JOIN molecule_structures cs ON m.molregno = cs.molregno
LEFT JOIN molecule_hierarchy h ON m.molregno = h.molregno AND h.parent_molregno IS NOT NULL
LEFT JOIN molecule_dictionary parent ON h.parent_molregno = parent.molregno
JOIN enzyme e ON m.met_id = e.met_id
WHERE t.organism = 'Mus musculus'
  AND s.standard_type = 'met_conversion'
  AND s.standard_relation = '='
  AND s.standard_value IS NOT NULL
  AND s.standard_units IS NOT NULL
ORDER BY canonical_smiles,
         substrate_compound_name,
         parent_compound_name,
         met_conversion,
         pathway_key,
         organism,
         enzyme_name
LIMIT 200
