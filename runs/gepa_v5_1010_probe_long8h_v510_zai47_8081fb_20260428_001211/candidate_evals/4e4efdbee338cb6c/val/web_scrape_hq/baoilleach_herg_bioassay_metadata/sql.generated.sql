SELECT 
  assays.chembl_id AS assay_chembl_id, 
  assays.tid, 
  assays.description AS assay_description, 
  target_dictionary.pref_name AS target_name, 
  target_dictionary.organism AS target_organism, 
  docs.journal, 
  docs.year, 
  docs.volume, 
  docs.first_page, 
  docs.doi
FROM assays
JOIN target_dictionary ON target_dictionary.tid = assays.tid
JOIN docs ON docs.doc_id = assays.doc_id
WHERE assays.assay_type = 'B' 
  AND assays.tid = 165
ORDER BY assays.chembl_id, assays.tid, docs.journal, docs.year, docs.doi
