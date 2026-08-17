SELECT a.chembl_id AS assay_chembl_id,
       a.tid AS tid,
       a.description AS assay_description,
       td.pref_name AS target_name,
       td.organism AS target_organism,
       d.journal,
       d.year,
       d.volume,
       d.first_page,
       d.doi
FROM assays a
JOIN activities act ON act.assay_id = a.assay_id
JOIN target_dictionary td ON td.tid = act.tid
JOIN docs d ON d.doc_id = a.doc_id
WHERE a.assay_type = 'B' AND td.tid = 165
ORDER BY a.chembl_id, a.tid, d.journal, d.year, d.doi;
