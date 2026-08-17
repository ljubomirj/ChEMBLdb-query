SELECT DISTINCT md.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary md
JOIN activities a ON md.molregno = a.molregno
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE td.pref_name = 'human serine/threonine-protein kinase PLK1' AND td.tax_id = 9606
ORDER BY molecule_chembl_id, canonical_smiles
LIMIT 2000
