SELECT
  compound_structures.canonical_smiles,
  molecule_dictionary.chembl_id,
  activities.standard_type,
  activities.standard_relation,
  activities.standard_value,
  activities.standard_units
FROM activities
INNER JOIN assays
  ON activities.assay_id = assays.assay_id
INNER JOIN molecule_dictionary
  ON activities.molregno = molecule_dictionary.molregno
INNER JOIN compound_structures
  ON activities.molregno = compound_structures.molregno
WHERE assays.chembl_id = 'CHEMBL1054500'
  AND activities.standard_relation = '='
  AND activities.standard_value IS NOT NULL
ORDER BY
  compound_structures.canonical_smiles,
  molecule_dictionary.chembl_id,
  activities.standard_type,
  activities.standard_relation,
  activities.standard_value,
  activities.standard_units
