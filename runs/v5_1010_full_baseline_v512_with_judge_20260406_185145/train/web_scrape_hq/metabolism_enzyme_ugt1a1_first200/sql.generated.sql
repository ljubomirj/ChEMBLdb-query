SELECT DISTINCT
  cs.canonical_smiles,
  sub.molregno AS substrate_compound_name,
  parent.molregno AS parent_compound_name,
  met.met_conversion,
  met.pathway_key,
  enzyme.organism,
  enzyme.pref_name AS enzyme_name
FROM metabolism met
JOIN compound_records cr ON met.substrate_record_id = cr.record_id
JOIN molecule_dictionary sub ON cr.molregno = sub.molregno
JOIN molecule_dictionary parent ON met.met_id = parent.molregno
JOIN target_dictionary enzyme ON sub.tid = enzyme.tid
JOIN compound_structures cs ON sub.molregno = cs.molregno
WHERE enzyme.pref_name = 'UGT1A1'
  AND enzyme.target_type = 'PROTEIN'
  AND enzyme.tax_id = 9606
  AND enzyme.organism = 'Homo sapiens'
  AND enzyme.tid = (SELECT tid FROM target_dictionary WHERE pref_name = 'UGT1A1' AND tax_id = 9606)
LIMIT 200
