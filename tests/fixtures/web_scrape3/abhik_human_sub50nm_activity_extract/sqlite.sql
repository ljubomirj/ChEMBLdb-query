SELECT DISTINCT
  molecule_dictionary.chembl_id,
  compound_structures.canonical_smiles,
  assays.tid,
  target_dictionary.chembl_id AS target_chembl_id,
  target_dictionary.organism,
  activities.activity_id,
  activities.standard_value,
  activities.standard_units,
  activities.data_validity_comment,
  assays.chembl_id AS assay_chembl_id
FROM molecule_dictionary
JOIN compound_structures ON compound_structures.molregno = molecule_dictionary.molregno
JOIN activities ON molecule_dictionary.molregno = activities.molregno
JOIN assays ON assays.assay_id = activities.assay_id
JOIN target_dictionary ON assays.tid = target_dictionary.tid
WHERE activities.standard_units = 'nM'
  AND activities.standard_value < 50
  AND target_dictionary.organism = 'Homo sapiens'
ORDER BY activities.standard_value
