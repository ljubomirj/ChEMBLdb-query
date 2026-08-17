SELECT DISTINCT td.pref_name AS target_description FROM target_dictionary td JOIN assays a ON td.tid = a.tid WHERE a.assay_organism = 'Plasmodium falciparum' ORDER BY td.pref_name
