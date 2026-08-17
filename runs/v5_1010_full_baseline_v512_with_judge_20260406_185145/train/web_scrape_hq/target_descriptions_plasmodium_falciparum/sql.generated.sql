SELECT DISTINCT td.pref_name AS target_description
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_records cr ON act.record_id = cr.record_id
JOIN docs d ON cr.doc_id = d.doc_id
WHERE a.assay_organism = 'Plasmodium falciparum'
  AND td.target_type = 'PROTEIN'
ORDER BY target_description;
