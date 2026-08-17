SELECT 
  child_molecule.chembl_id AS compound_chembl_id, 
  compound_structures.canonical_smiles, 
  compound_records.compound_key, 
  COALESCE(CAST(docs.pubmed_id AS TEXT), docs.doi) AS pubmed_id_or_doi, 
  assays.description AS assay_description, 
  activities.standard_type, 
  activities.standard_relation, 
  activities.standard_value, 
  activities.standard_units, 
  activities.activity_comment, 
  target_dictionary.chembl_id AS target_chembl_id, 
  target_dictionary.pref_name AS target_name, 
  target_dictionary.organism AS target_organism
FROM molecule_dictionary parent_molecule
JOIN molecule_hierarchy mh ON mh.parent_molregno = parent_molecule.molregno
JOIN molecule_dictionary child_molecule ON child_molecule.molregno = mh.molregno
JOIN compound_structures ON child_molecule.molregno = compound_structures.molregno
JOIN compound_records ON child_molecule.molregno = compound_records.molregno
JOIN activities ON compound_records.record_id = activities.record_id
JOIN assays ON activities.assay_id = assays.assay_id
JOIN docs ON activities.doc_id = docs.doc_id
JOIN target_dictionary ON assays.tid = target_dictionary.tid
WHERE parent_molecule.chembl_id = 'CHEMBL493620'
  AND target_dictionary.chembl_id = 'CHEMBL3879801'
  AND activities.standard_type = 'IC50'
ORDER BY 
  compound_chembl_id ASC, 
  canonical_smiles ASC, 
  compound_key ASC, 
  pubmed_id_or_doi ASC, 
  assay_description ASC, 
  standard_type ASC, 
  standard_relation ASC, 
  standard_value ASC, 
  standard_units ASC, 
  activity_comment ASC, 
  target_chembl_id ASC, 
  target_name ASC, 
  target_organism ASC
