SELECT DISTINCT td.pref_name AS target_description FROM target_dictionary td JOIN assays a ON a.tid = td.tid WHERE a.assay_organism = 'Cavia porcellus' ORDER BY td.pref_name ASC
