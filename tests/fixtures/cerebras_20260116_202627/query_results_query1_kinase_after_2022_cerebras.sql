SELECT
    compound_structures.canonical_smiles,
    molecule_dictionary.chembl_id,
    target_dictionary.pref_name AS target_name,
    docs.year,
    docs.doi,
    activities.standard_value AS IC50
FROM activities
JOIN assays ON activities.assay_id = assays.assay_id
JOIN docs ON assays.doc_id = docs.doc_id
JOIN molecule_dictionary ON activities.molregno = molecule_dictionary.molregno
JOIN compound_structures ON molecule_dictionary.molregno = compound_structures.molregno
JOIN target_dictionary ON assays.tid = target_dictionary.tid
JOIN target_components ON target_dictionary.tid = target_components.tid
JOIN component_class ON target_components.component_id = component_class.component_id
JOIN protein_classification ON component_class.protein_class_id = protein_classification.protein_class_id
WHERE activities.standard_type = 'IC50'
  AND docs.year > 2022
  AND protein_classification.pref_name LIKE '%Kinase%'
