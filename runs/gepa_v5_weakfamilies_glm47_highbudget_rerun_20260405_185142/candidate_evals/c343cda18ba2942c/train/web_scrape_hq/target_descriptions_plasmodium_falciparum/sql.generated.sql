SELECT DISTINCT td.pref_name AS target_description FROM assays a JOIN target_dictionary td ON a.tid = td.tid WHERE a.assay_organism = 'Plasmodium falciparum' ORDER BY target_description ASC
