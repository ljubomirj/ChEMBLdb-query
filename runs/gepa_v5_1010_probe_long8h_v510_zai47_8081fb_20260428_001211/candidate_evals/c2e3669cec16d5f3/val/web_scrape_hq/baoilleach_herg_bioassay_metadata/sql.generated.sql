SELECT
  a.chembl_id AS assay_chembl_id,
  a.tid,
  a.description AS assay_description,
  td.pref_name AS target_name,
  td.organism AS target_organism,
  d.journal,
  d.year,
  d.volume,
  d.first_page,
  d.doi
FROM assays a
INNER JOIN target_dictionary td ON td.tid = a.tid
INNER JOIN docs d ON d.doc_id = a.doc_id
WHERE a.assay_type = 'B'
  AND a.tid = 165
ORDER BY
  a.chembl_id ASC,
  a.tid ASC,
  d.journal ASC,
  d.year ASC,
  d.doi ASC
