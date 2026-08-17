SELECT DISTINCT md.chembl_id AS compound_chembl_id, cs.canonical_smiles
FROM molecule_dictionary md
JOIN activities a ON md.molregno = a.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE td.pref_name = 'Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit'
  AND ass.assay_type = 'B'
  AND ass.assay_organism = 'Homo sapiens'
ORDER BY compound_chembl_id;
