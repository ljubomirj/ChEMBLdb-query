SELECT d.doi,
       d.year,
       td.pref_name,
       td.chembl_id AS target_chembl_id,
       act.activity_id,
       cs.molregno,
       cs.canonical_smiles,
       act.standard_type,
       act.standard_value,
       act.standard_units
FROM compound_structures cs
JOIN activities act ON cs.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN docs d ON a.doc_id = d.doc_id
JOIN tmp_ids ON td.chembl_id = tmp_ids.chembl_id
WHERE d.year > 2022
  AND act.standard_type = 'IC50';
