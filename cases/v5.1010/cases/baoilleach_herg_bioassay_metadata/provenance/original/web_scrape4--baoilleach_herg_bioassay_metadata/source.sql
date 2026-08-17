SELECT t1.chembl_id, t1.tid, t1.description, t2.pref_name, t2.organism, t3.journal, t3.year, t3.volume, t3.first_page, t3.doi
FROM assays AS t1
INNER JOIN target_dictionary AS t2 ON t2.tid=t1.tid
INNER JOIN docs AS t3 ON t3.doc_id=t1.doc_id
WHERE t1.assay_type='B' AND t1.tid=165
ORDER BY t1.chembl_id;
