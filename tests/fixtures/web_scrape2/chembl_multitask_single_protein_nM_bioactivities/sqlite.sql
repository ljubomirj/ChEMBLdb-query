SELECT
  activities.doc_id AS doc_id,
  activities.standard_value AS standard_value,
  molecule_hierarchy.parent_molregno AS parent_molregno,
  compound_structures.canonical_smiles AS canonical_smiles,
  target_dictionary.tid AS tid,
  target_dictionary.chembl_id AS target_chembl_id,
  protein_classification.protein_class_desc AS protein_class_desc
FROM activities
JOIN assays ON activities.assay_id = assays.assay_id
JOIN target_dictionary ON assays.tid = target_dictionary.tid
JOIN target_components ON target_dictionary.tid = target_components.tid
JOIN component_class ON target_components.component_id = component_class.component_id
JOIN protein_classification ON component_class.protein_class_id = protein_classification.protein_class_id
JOIN molecule_dictionary ON activities.molregno = molecule_dictionary.molregno
JOIN molecule_hierarchy ON molecule_dictionary.molregno = molecule_hierarchy.molregno
JOIN compound_structures ON molecule_hierarchy.parent_molregno = compound_structures.molregno
WHERE activities.standard_units = 'nM'
  AND activities.standard_type IN ('EC50', 'IC50', 'Ki', 'Kd', 'XC50', 'AC50', 'Potency')
  AND activities.data_validity_comment IS NULL
  AND activities.standard_relation IN ('=', '<')
  AND activities.potential_duplicate = 0
  AND assays.confidence_score >= 8
  AND target_dictionary.target_type = 'SINGLE PROTEIN';
