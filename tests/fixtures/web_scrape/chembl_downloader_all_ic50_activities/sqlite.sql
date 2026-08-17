SELECT cs.canonical_smiles,
       md.chembl_id AS compound_chembl_id,
       act.bao_endpoint,
       act.standard_relation,
       act.standard_value,
       act.standard_units,
       a.assay_type,
       td.organism,
       a.tid,
       td.chembl_id AS target_chembl_id,
       td.pref_name AS target_name
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN activities act ON md.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE a.assay_type IN ('B', 'F')
  AND act.standard_value IS NOT NULL
  AND act.standard_units = 'nM'
  AND act.standard_relation IS NOT NULL
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '=';
