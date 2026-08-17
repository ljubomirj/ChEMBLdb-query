SELECT
  md.chembl_id,
  cs.canonical_smiles,
  act.standard_type,
  act.standard_value,
  act.standard_units
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN activities act ON md.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE td.chembl_id = 'CHEMBL221'
ORDER BY act.standard_value ASC, md.chembl_id, cs.canonical_smiles, act.standard_type, act.standard_value, act.standard_units
LIMIT 500
